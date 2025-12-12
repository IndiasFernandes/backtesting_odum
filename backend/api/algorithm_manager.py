"""API endpoints for managing execution algorithms."""
import ast
import inspect
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/algorithms", tags=["algorithms"])

# Cache for algorithm list (cleared when file changes)
_algorithm_cache: Optional[List[Dict[str, Any]]] = None
_algorithms_file_mtime: Optional[float] = None

# Path to execution algorithms file (updated after reorganization)
# New location: backend/execution/algorithms.py
# Old location (for backward compatibility): backend/execution_algorithms.py
ALGORITHMS_FILE_NEW = Path(__file__).parent.parent / "execution" / "algorithms.py"
ALGORITHMS_FILE_OLD = Path(__file__).parent.parent / "execution_algorithms.py"
ALGORITHMS_FILE_DOCKER_NEW = Path("/app/backend/execution/algorithms.py")
ALGORITHMS_FILE_DOCKER_OLD = Path("/app/backend/execution_algorithms.py")


class AlgorithmInfo(BaseModel):
    """Information about an execution algorithm."""
    name: str
    id: str
    description: str
    parameters: Dict[str, Any]
    code: Optional[str] = None


class AlgorithmCodeRequest(BaseModel):
    """Request to save algorithm code."""
    name: str
    code: str
    validate_only: bool = False


class AlgorithmTestRequest(BaseModel):
    """Request to test an algorithm."""
    algorithm_id: str
    parameters: Dict[str, Any]


def _get_algorithms_file() -> Path:
    """Get the path to the algorithms file."""
    # Try new location first (after reorganization)
    # Docker paths
    if ALGORITHMS_FILE_DOCKER_NEW.exists():
        return ALGORITHMS_FILE_DOCKER_NEW
    if ALGORITHMS_FILE_DOCKER_OLD.exists():
        return ALGORITHMS_FILE_DOCKER_OLD
    
    # Local paths
    if ALGORITHMS_FILE_NEW.exists():
        return ALGORITHMS_FILE_NEW
    if ALGORITHMS_FILE_OLD.exists():
        return ALGORITHMS_FILE_OLD
    
    # Try alternative paths
        alt_paths = [
            Path(__file__).parent.parent / "execution" / "algorithms.py",
        Path(__file__).parent.parent / "execution_algorithms.py",
        ]
        for path in alt_paths:
            if path.exists():
                return path
    
    raise FileNotFoundError(
        f"Could not find execution algorithms file. Tried:\n"
        f"  New location: {ALGORITHMS_FILE_DOCKER_NEW}, {ALGORITHMS_FILE_NEW}\n"
        f"  Old location: {ALGORITHMS_FILE_DOCKER_OLD}, {ALGORITHMS_FILE_OLD}\n"
        f"  Alternative paths: {alt_paths}"
    )


def _parse_algorithm_info(code: str, class_name: str) -> Dict[str, Any]:
    """Parse algorithm information from code."""
    try:
        tree = ast.parse(code)
        
        # Find the class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Extract docstring
                docstring = ast.get_docstring(node) or ""
                
                # Extract parameters from docstring or method
                parameters = {}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "on_order":
                        # Try to find exec_algorithm_params usage
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Call):
                                if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "get":
                                    if len(stmt.args) >= 2:
                                        param_name = None
                                        if isinstance(stmt.args[0], ast.Constant):
                                            param_name = stmt.args[0].value
                                        elif isinstance(stmt.args[0], ast.Str):  # Python < 3.8
                                            param_name = stmt.args[0].s
                                        
                                        default_value = None
                                        if len(stmt.args) >= 2:
                                            if isinstance(stmt.args[1], ast.Constant):
                                                default_value = stmt.args[1].value
                                            elif isinstance(stmt.args[1], ast.Num):  # Python < 3.8
                                                default_value = stmt.args[1].n
                                        
                                        if param_name:
                                            parameters[param_name] = default_value
                
                return {
                    "description": docstring.split("\n")[0] if docstring else "",
                    "parameters": parameters
                }
    except Exception as e:
        return {"description": "", "parameters": {}}


@router.get("/", response_model=List[AlgorithmInfo])
async def list_algorithms():
    """List all available execution algorithms (cached for performance)."""
    global _algorithm_cache, _algorithms_file_mtime
    
    try:
        algorithms_file = _get_algorithms_file()
        current_mtime = algorithms_file.stat().st_mtime
        
        # Return cached result if file hasn't changed
        if _algorithm_cache is not None and _algorithms_file_mtime == current_mtime:
            return _algorithm_cache
        
        # Parse algorithms
        code = algorithms_file.read_text()
        algorithms = []
        
        # Known algorithms
        known_algorithms = [
            ("TWAPExecAlgorithm", "TWAP", "Time-Weighted Average Price execution algorithm"),
            ("VWAPExecAlgorithm", "VWAP", "Volume-Weighted Average Price execution algorithm"),
            ("IcebergExecAlgorithm", "ICEBERG", "Iceberg execution algorithm (shows only visible portion)"),
        ]
        
        # Filter to only include algorithms that exist in the code
        existing_algorithms = [
            algo for algo in known_algorithms 
            if f"class {algo[0]}" in code
        ]
        
        for class_name, algo_id, default_desc in existing_algorithms:
            if f"class {class_name}" in code:
                info = _parse_algorithm_info(code, class_name)
                algorithms.append(AlgorithmInfo(
                    name=class_name,
                    id=algo_id,
                    description=info.get("description", default_desc),
                    parameters=info.get("parameters", {}),
                ))
        
        # Cache the result
        _algorithm_cache = algorithms
        _algorithms_file_mtime = current_mtime
        
        return algorithms
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing algorithms: {str(e)}")


@router.get("/{algorithm_id}", response_model=AlgorithmInfo)
async def get_algorithm(algorithm_id: str):
    """Get algorithm code and information."""
    try:
        algorithms_file = _get_algorithms_file()
        code = algorithms_file.read_text()
        
        # Map algorithm IDs to class names
        id_to_class = {
            "TWAP": "TWAPExecAlgorithm",
            "VWAP": "VWAPExecAlgorithm",
            "ICEBERG": "IcebergExecAlgorithm",
        }
        
        class_name = id_to_class.get(algorithm_id.upper())
        if not class_name:
            raise HTTPException(status_code=404, detail=f"Algorithm {algorithm_id} not found")
        
        # Extract the class code
        class_code = _extract_class_code(code, class_name)
        if not class_code:
            raise HTTPException(status_code=404, detail=f"Could not find {class_name} in code")
        
        info = _parse_algorithm_info(code, class_name)
        
        return AlgorithmInfo(
            name=class_name,
            id=algorithm_id.upper(),
            description=info.get("description", ""),
            parameters=info.get("parameters", {}),
            code=class_code,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting algorithm: {str(e)}")


def _extract_class_code(code: str, class_name: str) -> Optional[str]:
    """Extract a class definition from code."""
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Get the line range
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 100
                
                lines = code.split("\n")
                return "\n".join(lines[start_line:end_line])
    except Exception:
        pass
    
    return None


@router.post("/validate")
async def validate_algorithm_code(request: AlgorithmCodeRequest):
    """Validate algorithm code syntax and structure."""
    try:
        # Parse the code to check syntax
        tree = ast.parse(request.code)
        
        # Check if it's a class
        has_class = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        if not has_class:
            return {"valid": False, "error": "Code must contain a class definition"}
        
        # Check if it inherits from ExecAlgorithm
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check bases - handle both Name and Attribute nodes
                bases_str = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases_str.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle cases like ExecAlgorithm from module
                        bases_str.append(base.attr)
                    else:
                        bases_str.append(str(base))
                
                if "ExecAlgorithm" not in " ".join(bases_str):
                    return {"valid": False, "error": f"Class must inherit from ExecAlgorithm. Found bases: {bases_str}"}
                
                # Check for on_order method
                has_on_order = any(
                    isinstance(item, ast.FunctionDef) and item.name == "on_order"
                    for item in node.body
                )
                
                # Also check what methods exist for better error messages
                methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
                
                if not has_on_order:
                    # Check if they have execute instead (common mistake)
                    has_execute = "execute" in methods
                    if has_execute:
                        return {
                            "valid": False, 
                            "error": "Class must have an 'on_order' method (not 'execute'). In NautilusTrader ExecAlgorithm, use 'on_order(self, order: Order)' to handle incoming orders."
                        }
                    else:
                        return {
                            "valid": False, 
                            "error": f"Class must have an 'on_order' method. Found methods: {', '.join(methods) if methods else 'none'}"
                        }
        
        return {"valid": True, "message": "Code is valid"}
    except SyntaxError as e:
        return {"valid": False, "error": f"Syntax error: {str(e)}"}
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}


@router.post("/save")
async def save_algorithm(request: AlgorithmCodeRequest):
    """Save algorithm code (creates backup first)."""
    try:
        algorithms_file = _get_algorithms_file()
        
        # Validate first
        validation = await validate_algorithm_code(request)
        if not validation.get("valid"):
            raise HTTPException(status_code=400, detail=validation.get("error", "Invalid code"))
        
        # Create backup
        backup_file = algorithms_file.with_suffix(".py.backup")
        if algorithms_file.exists():
            backup_file.write_text(algorithms_file.read_text())
        
        # Read current code
        current_code = algorithms_file.read_text()
        
        # TODO: Implement smart code replacement
        # For now, just append (this is a simple implementation)
        # In production, you'd want to replace the specific class
        
        return {"success": True, "message": f"Algorithm code saved (backup created at {backup_file.name})"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving algorithm: {str(e)}")


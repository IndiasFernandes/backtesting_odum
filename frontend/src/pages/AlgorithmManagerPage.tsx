import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backtestApi, AlgorithmInfo, AlgorithmCodeRequest } from '../services/api'
import { useToastContext } from '../components/Layout'

export default function AlgorithmManagerPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string | null>(null)
  const [editingCode, setEditingCode] = useState<string>('')
  const [isEditing, setIsEditing] = useState(false)
  const [validationResult, setValidationResult] = useState<{ valid: boolean; error?: string; message?: string } | null>(null)

  // Fetch list of algorithms
  const { data: algorithms, isLoading } = useQuery({
    queryKey: ['algorithms'],
    queryFn: () => backtestApi.listAlgorithms(),
  })

  // Fetch selected algorithm details
  const { data: algorithmDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ['algorithm', selectedAlgorithm],
    queryFn: () => backtestApi.getAlgorithm(selectedAlgorithm!),
    enabled: !!selectedAlgorithm && !isEditing,
  })

  // Validate code mutation
  const validateMutation = useMutation({
    mutationFn: (request: AlgorithmCodeRequest) => backtestApi.validateAlgorithmCode(request),
    onSuccess: (data) => {
      setValidationResult(data)
      if (data.valid) {
        toast({ type: 'success', message: 'Code is valid!' })
      } else {
        toast({ type: 'error', message: data.error || 'Code validation failed' })
      }
    },
  })

  // Save algorithm mutation
  const saveMutation = useMutation({
    mutationFn: (request: AlgorithmCodeRequest) => backtestApi.saveAlgorithm(request),
    onSuccess: (data) => {
      toast({ type: 'success', message: data.message || 'Algorithm saved successfully' })
      setIsEditing(false)
      queryClient.invalidateQueries({ queryKey: ['algorithms'] })
      queryClient.invalidateQueries({ queryKey: ['algorithm', selectedAlgorithm] })
    },
    onError: (error: any) => {
      toast({ type: 'error', message: error.response?.data?.detail || 'Failed to save algorithm' })
    },
  })

  // Initialize editing code when algorithm is selected
  useEffect(() => {
    if (algorithmDetails?.code && !isEditing) {
      setEditingCode(algorithmDetails.code)
    }
  }, [algorithmDetails, isEditing])

  const handleSelectAlgorithm = (algorithmId: string) => {
    setSelectedAlgorithm(algorithmId)
    setIsEditing(false)
    setValidationResult(null)
  }

  const handleEdit = () => {
    setIsEditing(true)
    setValidationResult(null)
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditingCode(algorithmDetails?.code || '')
    setValidationResult(null)
  }

  const handleValidate = () => {
    if (!selectedAlgorithm || !editingCode) return
    
    validateMutation.mutate({
      name: selectedAlgorithm,
      code: editingCode,
      validate_only: true,
    })
  }

  const handleSave = () => {
    if (!selectedAlgorithm || !editingCode) return
    
    if (!validationResult?.valid) {
      toast({ type: 'warning', message: 'Please validate code before saving' })
      return
    }
    
    saveMutation.mutate({
      name: selectedAlgorithm,
      code: editingCode,
      validate_only: false,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Execution Algorithms Manager</h2>
        <p className="text-gray-400">View, edit, and create execution algorithms for order management</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Algorithm List */}
        <div className="lg:col-span-1">
          <div className="bg-dark-surface border border-dark-border rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">Algorithms</h3>
            {isLoading ? (
              <div className="text-gray-400">Loading...</div>
            ) : (
              <div className="space-y-2">
                {algorithms?.map((algo) => (
                  <button
                    key={algo.id}
                    onClick={() => handleSelectAlgorithm(algo.id)}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                      selectedAlgorithm === algo.id
                        ? 'border-blue-500 bg-blue-900/30'
                        : 'border-dark-border bg-dark-bg hover:border-gray-600'
                    }`}
                  >
                    <div className="font-semibold text-white">{algo.id}</div>
                    <div className="text-sm text-gray-400 mt-1">{algo.description}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Algorithm Details & Editor */}
        <div className="lg:col-span-2">
          {selectedAlgorithm ? (
            <div className="bg-dark-surface border border-dark-border rounded-lg p-6">
              {isLoadingDetails ? (
                <div className="text-gray-400">Loading algorithm details...</div>
              ) : algorithmDetails ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-2xl font-semibold text-white">{algorithmDetails.id}</h3>
                      <p className="text-gray-400 mt-1">{algorithmDetails.description}</p>
                    </div>
                    {!isEditing ? (
                      <button
                        onClick={handleEdit}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Edit
                      </button>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={handleCancel}
                          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleValidate}
                          disabled={validateMutation.isPending}
                          className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 transition-colors"
                        >
                          {validateMutation.isPending ? 'Validating...' : 'Validate'}
                        </button>
                        <button
                          onClick={handleSave}
                          disabled={saveMutation.isPending || !validationResult?.valid}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                        >
                          {saveMutation.isPending ? 'Saving...' : 'Save'}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Parameters */}
                  {Object.keys(algorithmDetails.parameters).length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-semibold text-white mb-2">Parameters</h4>
                      <div className="bg-dark-bg border border-dark-border p-3 rounded">
                        <pre className="text-sm text-gray-300 font-mono">
                          {JSON.stringify(algorithmDetails.parameters, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Validation Result */}
                  {validationResult && (
                    <div className={`mb-4 p-3 rounded border ${
                      validationResult.valid 
                        ? 'bg-green-900/30 border-green-700' 
                        : 'bg-red-900/30 border-red-700'
                    }`}>
                      {validationResult.valid ? (
                        <div className="text-green-300">✓ {validationResult.message || 'Code is valid'}</div>
                      ) : (
                        <div className="text-red-300">✗ {validationResult.error || 'Validation failed'}</div>
                      )}
                    </div>
                  )}

                  {/* Code Editor */}
                  <div>
                    <h4 className="font-semibold text-white mb-2">Code</h4>
                    <textarea
                      value={editingCode}
                      onChange={(e) => setEditingCode(e.target.value)}
                      disabled={!isEditing}
                      className={`w-full h-96 p-4 font-mono text-sm border rounded-lg ${
                        isEditing 
                          ? 'border-blue-500 bg-dark-bg text-white focus:border-blue-400 focus:outline-none' 
                          : 'border-dark-border bg-dark-bg/50 text-gray-400'
                      }`}
                      style={{ fontFamily: 'monospace' }}
                    />
                    {isEditing && (
                      <div className="mt-2 text-sm text-gray-400">
                        <p>• Make sure your class inherits from <code className="bg-dark-bg px-1 rounded text-gray-300">ExecAlgorithm</code></p>
                        <p>• Include an <code className="bg-dark-bg px-1 rounded text-gray-300">on_order</code> method</p>
                        <p>• Validate before saving</p>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="text-gray-400">Algorithm not found</div>
              )}
            </div>
          ) : (
            <div className="bg-dark-surface border border-dark-border rounded-lg p-6 text-center text-gray-400">
              Select an algorithm to view and edit
            </div>
          )}
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
        <h4 className="font-semibold text-blue-300 mb-2">Quick Guide</h4>
        <ul className="text-sm text-blue-200 space-y-1">
          <li>• Select an algorithm from the list to view its code</li>
          <li>• Click "Edit" to modify the algorithm code</li>
          <li>• Click "Validate" to check your code before saving</li>
          <li>• Click "Save" to update the algorithm (backup is created automatically)</li>
          <li>• See <code className="bg-dark-bg px-1 rounded text-blue-100">EXECUTION_ALGORITHMS_CUSTOMIZATION_GUIDE.md</code> for detailed documentation</li>
        </ul>
      </div>
    </div>
  )
}


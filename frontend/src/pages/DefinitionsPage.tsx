import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { backtestApi } from '../services/api'
import { useToastContext } from '../components/Layout'

export default function DefinitionsPage() {
  const [selectedConfig, setSelectedConfig] = useState<string>('')
  const [configContent, setConfigContent] = useState<string>('')
  const toast = useToastContext()

  const { data: configs, isLoading, error } = useQuery({
    queryKey: ['configs'],
    queryFn: () => backtestApi.getConfigs(),
  })

  const handleConfigSelect = async (configName: string) => {
    setSelectedConfig(configName)
    try {
      const config = await backtestApi.getConfig(configName)
      setConfigContent(JSON.stringify(config, null, 2))
    } catch (error) {
      console.error('Error loading config:', error)
      setConfigContent('{}')
      toast.error('Failed to load config')
    }
  }

  const handleSave = async () => {
    if (!selectedConfig) return
    try {
      const parsed = JSON.parse(configContent)
      await backtestApi.saveConfig(selectedConfig, parsed)
      toast.success('Config saved successfully')
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        toast.error('Invalid JSON format')
      } else {
        toast.error(`Error saving config: ${error.message || error}`)
      }
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Config Definitions</h2>
      
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-dark-surface border border-dark-border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Available Configs</h3>
          <div className="space-y-2">
            {isLoading && (
              <p className="text-gray-400">Loading configs...</p>
            )}
            {error && (
              <div className="text-red-400">
                <p className="font-semibold">Error loading configs:</p>
                <p className="text-sm mt-1">{error instanceof Error ? error.message : String(error)}</p>
              </div>
            )}
            {!isLoading && !error && configs && configs.length === 0 && (
              <p className="text-gray-400">No configs found</p>
            )}
            {!isLoading && !error && configs && configs.length > 0 && configs.map((config) => (
              <button
                key={config}
                onClick={() => handleConfigSelect(config)}
                className={`w-full text-left px-4 py-2 rounded ${
                  selectedConfig === config
                    ? 'bg-blue-600 text-white'
                    : 'bg-dark-bg text-gray-300 hover:bg-dark-surface'
                }`}
              >
                {config}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-dark-surface border border-dark-border rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Config Editor</h3>
          {selectedConfig ? (
            <>
              <textarea
                value={configContent}
                onChange={(e) => setConfigContent(e.target.value)}
                className="w-full h-96 bg-dark-bg border border-dark-border rounded p-4 text-sm text-white font-mono"
                placeholder="Config JSON content..."
              />
              <button
                onClick={handleSave}
                className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg"
              >
                Save Config
              </button>
            </>
          ) : (
            <p className="text-gray-400">Select a config to edit</p>
          )}
        </div>
      </div>
    </div>
  )
}


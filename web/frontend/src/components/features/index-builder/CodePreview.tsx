import { useState } from 'react'
import { IndexConfiguration } from '../../../types'
import { generatePythonCode, generateYAML } from '@/lib/codegen'

interface CodePreviewProps {
  config: IndexConfiguration
}

type CodeFormat = 'python' | 'yaml' | 'json'

export function CodePreview({ config }: CodePreviewProps) {
  const [format, setFormat] = useState<CodeFormat>('python')
  const [copied, setCopied] = useState(false)

  const generateJSON = (): string => {
    return JSON.stringify(config, null, 2)
  }

  const getCode = (): string => {
    switch (format) {
      case 'python':
        return generatePythonCode(config)
      case 'yaml':
        return generateYAML(config)
      case 'json':
        return generateJSON()
    }
  }

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(getCode())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadFile = () => {
    const code = getCode()
    const ext = format === 'python' ? 'py' : format
    const filename = `${config.basics.identifier || 'index'}.${ext}`
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Generated Code</span>
          <div className="flex bg-gray-200 rounded-lg p-0.5">
            {(['python', 'yaml', 'json'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${format === f
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                  }`}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            {copied ? (
              <>
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
          <button
            onClick={downloadFile}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
        </div>
      </div>

      {/* Code Area */}
      <div className="flex-1 overflow-auto bg-gray-900 p-4">
        <pre className="text-sm font-mono text-gray-100 whitespace-pre-wrap">
          <code>{getCode()}</code>
        </pre>
      </div>
    </div>
  )
}

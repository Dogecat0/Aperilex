import React, { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Hash,
  Type,
  List,
  FileText,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import { type ContentItem, formatKey, getCategoryColors } from '@/utils/analysisHelpers'
import { IconCard } from '@/components/ui/Card'

interface ContentRendererProps {
  item: ContentItem
  className?: string
}

export function ContentRenderer({ item, className = '' }: ContentRendererProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  const toggleItem = (path: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedItems(newExpanded)
  }

  const getValueIcon = (type: ContentItem['type']) => {
    switch (type) {
      case 'array':
        return List
      case 'object':
        return FileText
      case 'boolean':
        return ToggleLeft
      case 'number':
        return Hash
      default:
        return Type
    }
  }

  const renderValue = (value: any, path: string, level: number = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">Not provided</span>
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400 italic">No items</span>
      }

      const isExpanded = expandedItems.has(path)
      const hasComplexItems = value.some((item) => typeof item === 'object' && item !== null)

      return (
        <div>
          <button
            onClick={() => toggleItem(path)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <List className="h-4 w-4" />
            {value.length} item{value.length !== 1 ? 's' : ''}
          </button>

          {isExpanded && (
            <div className={`mt-3 ${level < 2 ? 'ml-4' : 'ml-2'} space-y-2`}>
              {value.map((item, index) => (
                <div
                  key={index}
                  className={`${
                    hasComplexItems
                      ? 'p-3 bg-gray-50 rounded-lg border border-gray-200'
                      : 'p-2 bg-gray-25 rounded text-sm'
                  } transition-colors hover:bg-gray-100`}
                >
                  {typeof item === 'object' && item !== null ? (
                    renderValue(item, `${path}[${index}]`, level + 1)
                  ) : (
                    <div className="text-gray-700">{String(item)}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'object' && value !== null) {
      const keys = Object.keys(value)

      if (keys.length === 0) {
        return <span className="text-gray-400 italic">No content</span>
      }

      const isExpanded = expandedItems.has(path)

      return (
        <div>
          <button
            onClick={() => toggleItem(path)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <FileText className="h-4 w-4" />
            {keys.length} field{keys.length !== 1 ? 's' : ''}
          </button>

          {isExpanded && (
            <div className={`mt-3 ${level < 2 ? 'ml-4' : 'ml-2'} space-y-3`}>
              {keys.map((key) => (
                <div
                  key={key}
                  className="border-l-3 border-blue-200 pl-4 hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <div className="font-medium text-sm text-gray-900 min-w-0 flex-1">
                      {formatKey(key)}
                    </div>
                  </div>
                  <div className="mt-2">{renderValue(value[key], `${path}.${key}`, level + 1)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'boolean') {
      const Icon = value ? ToggleRight : ToggleLeft
      return (
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${value ? 'text-emerald-600' : 'text-gray-400'}`} />
          <span className={`font-medium ${value ? 'text-emerald-700' : 'text-gray-500'}`}>
            {value ? 'Yes' : 'No'}
          </span>
        </div>
      )
    }

    if (typeof value === 'number') {
      return (
        <div className="flex items-center gap-2">
          <Hash className="h-4 w-4 text-blue-500" />
          <span className="text-gray-700 font-mono font-medium">{value.toLocaleString()}</span>
        </div>
      )
    }

    // String values
    const stringValue = String(value)
    if (stringValue.length > 300) {
      const isExpanded = expandedItems.has(`${path}_text`)
      return (
        <div className="text-sm">
          <div className="text-gray-700 leading-relaxed">
            {isExpanded ? stringValue : `${stringValue.substring(0, 300)}...`}
          </div>
          <button
            onClick={() => toggleItem(`${path}_text`)}
            className="text-primary-600 hover:text-primary-700 text-sm mt-2 font-medium inline-flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" />
                Show more
              </>
            )}
          </button>
        </div>
      )
    }

    return <span className="text-gray-700 leading-relaxed text-sm">{stringValue}</span>
  }

  const colors = getCategoryColors(item.category)
  const ValueIcon = getValueIcon(item.type)

  return (
    <IconCard
      icon={ValueIcon}
      title={formatKey(item.key)}
      iconColor={colors.icon}
      className={`transition-all hover:shadow-md ${
        item.isSignificant ? 'border-blue-200 bg-blue-50/30' : 'border-gray-200'
      } ${className}`}
    >
      <div className="flex items-center gap-2 mb-2">
        {item.isSignificant && (
          <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
            Key
          </span>
        )}
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${colors.badge}`}>
          {formatKey(item.category)}
        </span>
      </div>
      <div>{renderValue(item.value, item.key.toLowerCase().replace(/\s+/g, '_'))}</div>
    </IconCard>
  )
}

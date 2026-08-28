import { memo } from 'react'

function renderInlineStyles(text: string) {
  const parts = text.split(/(\*\*.*?\*\*|\[\d+(?:,\s*\d+)*\])/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('[') && part.endsWith(']')) {
      return (
        <span key={idx} className="citation-badge">
          {part}
        </span>
      )
    }
    return part
  })
}

interface MarkdownBlock {
  type: 'h3' | 'list' | 'p'
  text?: string
  items?: string[]
}

function parseMarkdownToBlocks(text: string): MarkdownBlock[] {
  const lines = text.split('\n')
  const blocks: MarkdownBlock[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    if (!trimmed) continue

    if (trimmed.startsWith('## ')) {
      blocks.push({ type: 'h3', text: trimmed.replace(/^##\s+/, '') })
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const itemText = trimmed.replace(/^[-*]\s+/, '')
      const lastBlock = blocks[blocks.length - 1]
      if (lastBlock && lastBlock.type === 'list' && lastBlock.items) {
        lastBlock.items.push(itemText)
      } else {
        blocks.push({ type: 'list', items: [itemText] })
      }
    } else {
      blocks.push({ type: 'p', text: line })
    }
  }
  return blocks
}

interface MarkdownRendererProps {
  text: string
}

export const MarkdownRenderer = memo(function MarkdownRenderer({ text }: MarkdownRendererProps) {
  if (!text) return null
  const blocks = parseMarkdownToBlocks(text)

  return (
    <div className="markdown-content">
      {blocks.map((block, idx) => {
        if (block.type === 'h3') {
          return (
            <h3 key={idx} className="markdown-h3">
              {renderInlineStyles(block.text!)}
            </h3>
          )
        }
        if (block.type === 'list') {
          return (
            <ul key={idx} className="markdown-ul">
              {block.items!.map((item, itemIdx) => (
                <li key={itemIdx} className="markdown-li">
                  {renderInlineStyles(item)}
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={idx} className="markdown-p">
            {renderInlineStyles(block.text!)}
          </p>
        )
      })}
    </div>
  )
})

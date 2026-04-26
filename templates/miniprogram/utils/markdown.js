/**
 * Lightweight Markdown → rich-text nodes converter for WeChat Mini Program.
 * Supports: headings, bold, italic, inline code, code blocks, links, lists,
 * blockquotes, horizontal rules, tables, paragraphs.
 */

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function parseInline(text) {
  // Order matters: code first (to avoid conflicts), then bold, italic, links, images
  return text
    // inline code
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    // images (before links)
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8rpx;margin:8rpx 0;" />')
    // links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a style="color:#1ee07f;text-decoration:underline;">$1</a>')
    // bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // strikethrough
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
}

function isTableSeparator(line) {
  return /^\|?[\s:]*-{2,}[\s:]*(\|[\s:]*-{2,}[\s:]*)*\|?\s*$/.test(line.trim())
}

function parseTableRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim())
}

function markdownToHtml(md) {
  if (!md) return ''

  const lines = md.split('\n')
  let html = ''
  let inCodeBlock = false
  let codeContent = ''
  let inList = false
  let listType = '' // 'ul' or 'ol'

  function closeList() {
    if (inList) {
      html += `</${listType}>`
      inList = false
      listType = ''
    }
  }

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]

    // Code block toggle
    if (line.trimStart().startsWith('```')) {
      if (!inCodeBlock) {
        closeList()
        inCodeBlock = true
        codeContent = ''
      } else {
        html += '<pre class="md-pre"><code>' + escapeHtml(codeContent.trimEnd()) + '</code></pre>'
        inCodeBlock = false
      }
      continue
    }

    if (inCodeBlock) {
      codeContent += line + '\n'
      continue
    }

    // Horizontal rule
    if (/^(\*{3,}|-{3,}|_{3,})\s*$/.test(line.trim())) {
      closeList()
      html += '<hr class="md-hr" />'
      continue
    }

    // Empty line
    if (line.trim() === '') {
      closeList()
      continue
    }

    // Table detection: current line has pipes, next line is separator
    if (line.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      closeList()
      const headers = parseTableRow(line)
      i++ // skip separator line
      html += '<table class="md-table"><thead><tr>'
      headers.forEach(h => { html += '<th>' + parseInline(escapeHtml(h)) + '</th>' })
      html += '</tr></thead><tbody>'
      // Parse body rows
      while (i + 1 < lines.length && lines[i + 1].includes('|') && lines[i + 1].trim() !== '') {
        i++
        const cells = parseTableRow(lines[i])
        html += '<tr>'
        cells.forEach(c => { html += '<td>' + parseInline(escapeHtml(c)) + '</td>' })
        html += '</tr>'
      }
      html += '</tbody></table>'
      continue
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/)
    if (headingMatch) {
      closeList()
      const level = headingMatch[1].length
      const text = parseInline(escapeHtml(headingMatch[2]))
      html += `<h${level} class="md-h md-h${level}">${text}</h${level}>`
      continue
    }

    // Blockquote
    if (line.trimStart().startsWith('> ')) {
      closeList()
      const text = parseInline(escapeHtml(line.replace(/^>\s*/, '')))
      html += `<blockquote class="md-quote">${text}</blockquote>`
      continue
    }

    // Unordered list
    const ulMatch = line.match(/^(\s*)[*\-+]\s+(.+)/)
    if (ulMatch) {
      if (!inList || listType !== 'ul') {
        closeList()
        html += '<ul class="md-list">'
        inList = true
        listType = 'ul'
      }
      html += `<li>${parseInline(escapeHtml(ulMatch[2]))}</li>`
      continue
    }

    // Ordered list
    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)/)
    if (olMatch) {
      if (!inList || listType !== 'ol') {
        closeList()
        html += '<ol class="md-list">'
        inList = true
        listType = 'ol'
      }
      html += `<li>${parseInline(escapeHtml(olMatch[2]))}</li>`
      continue
    }

    // Paragraph
    closeList()
    html += `<p class="md-p">${parseInline(escapeHtml(line))}</p>`
  }

  // Close any remaining open blocks
  if (inCodeBlock) {
    html += '<pre class="md-pre"><code>' + escapeHtml(codeContent.trimEnd()) + '</code></pre>'
  }
  closeList()

  return html
}

module.exports = { markdownToHtml }

import { useState } from 'react'

// Only talks to the outside via onSubmit(text), so a speech-to-text layer can
// call the same handler later.
export default function AnswerInput({ onSubmit, disabled }) {
  const [value, setValue] = useState('')

  function submit() {
    const text = value.trim()
    if (!text || disabled) return
    setValue('')
    onSubmit(text)
  }

  return (
    <div className="answer">
      <textarea
        rows={3}
        value={value}
        disabled={disabled}
        placeholder="Type your answer… (Enter to send, Shift+Enter for newline)"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
      />
      <button className="primary" onClick={submit} disabled={disabled || !value.trim()}>Send</button>
    </div>
  )
}

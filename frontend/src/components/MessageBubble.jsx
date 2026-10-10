// Single place interviewer/candidate text is rendered — voice (TTS) can wrap this later.
export default function MessageBubble({ message }) {
  return (
    <div className={`bubble ${message.sender}`}>
      <div className="who">{message.sender === 'interviewer' ? 'Interviewer' : 'You'}</div>
      <div className="text">{message.content}</div>
    </div>
  )
}

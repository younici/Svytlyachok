import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
        <div className="app">
      <h1>Мой первый React</h1>

      <p>Счётчик: {count}</p>

      <button onClick={() => setCount(count + 1)}>
        +1
      </button>
    </div>
    </>
  )
}

export default App

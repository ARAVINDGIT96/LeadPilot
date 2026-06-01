import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './index.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex flex-col items-center justify-center text-white p-8">
        <a href="https://vitejs.dev" target="_blank" rel="noreferrer">
          <img src={viteLogo} className="h-24 w-24 animate-spin mb-4" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="h-24 w-24 mb-4" alt="React logo" />
        </a>
        <h1 className="text-4xl font-bold mb-8 text-center">
          LeadPilot Frontend
        </h1>
        <div className="max-w-md w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl">
          <button
            className="bg-white/20 hover:bg-white/30 px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 mb-4 w-full"
            onClick={() => setCount((count) => count + 1)}
          >
            count is {count}
          </button>
          <p className="text-center opacity-80">
            Ready for LeadPilot integration
          </p>
        </div>
        <p className="mt-8 text-xl opacity-80 text-center">
          Edit <code className="bg-white/20 px-2 py-1 rounded font-mono">src/App.jsx</code> and save to test HMR
        </p>
      </div>
    </>
  )
}

export default App


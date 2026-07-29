import ReactDOM from 'react-dom/client'
import App from './App'

// ═══ STRICT MODE DESLIGADO ═══
// React StrictMode causa double-mount em desenvolvimento,
// o que quebra o Canvas do R3F (cria/reseta contexto WebGL duas vezes).
// R3F v9 + React 19 não são totalmente compatíveis com StrictMode.
//
// Assim que o ecossistema R3F estabilizar suporte a React 19,
// podemos reativar: <React.StrictMode><App /></React.StrictMode>

ReactDOM.createRoot(document.getElementById('root')!).render(<App />)


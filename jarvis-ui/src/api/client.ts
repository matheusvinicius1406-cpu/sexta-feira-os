export class KernelClient {
  private baseUrl: string

  constructor(baseUrl = '') {
    this.baseUrl = baseUrl || '/api'
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = localStorage.getItem('jarvis_token')
    if (token) headers['Authorization'] = `Bearer ${token}`
    return headers
  }

  async login(email: string, password: string): Promise<string> {
    const res = await fetch(`${this.baseUrl}/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) throw new Error(`Login failed: ${res.status}`)
    const data = await res.json()
    localStorage.setItem('jarvis_token', data.access_token)
    localStorage.setItem('jarvis_owner_id', data.owner_id)
    return data.access_token
  }

  async health() {
    const res = await fetch(`${this.baseUrl}/v1/health`)
    return res.json()
  }

  async chat(message: string): Promise<string> {
    const res = await fetch(`${this.baseUrl}/v1/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ message }),
    })
    if (!res.ok) throw new Error(`Chat error: ${res.status}`)
    const data = await res.json()
    return data.reply
  }

  async getMemories() {
    const res = await fetch(`${this.baseUrl}/v1/memory`, {
      headers: this.getHeaders(),
    })
    if (!res.ok) throw new Error(`Memory error: ${res.status}`)
    return res.json()
  }

  async teach(content: string) {
    const res = await fetch(`${this.baseUrl}/v1/memory`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error(`Teach error: ${res.status}`)
    return res.json()
  }
}

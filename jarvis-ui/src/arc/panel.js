/**
 * The module panel — where a sub-item's reading is shown.
 *
 * Renders exactly one of four outcomes, and they must stay visually distinct
 * because they mean different things to whoever is looking:
 *
 *   loading   the request is in flight
 *   rows      the kernel answered; this is what it said
 *   absent    this OS genuinely lacks the capability, and here is why
 *   error     something is wrong and can be fixed — shown in the breach colour
 *
 * Collapsing `absent` into `error` would tell the owner their system is broken
 * when it is merely honest; collapsing `error` into an empty list would hide a
 * kernel that is refusing them. Both were tempting and both are wrong.
 */
import { panelFor } from './modules.js'

const el = {}
let token = 0

function init() {
  if (el.root) return
  el.root = document.getElementById('panel')
  el.title = document.getElementById('pnTitle')
  el.src = document.getElementById('pnSrc')
  el.body = document.getElementById('pnBody')
}

function clear() {
  el.body.replaceChildren()
}

function add(cls, text) {
  const d = document.createElement('div')
  d.className = cls
  d.textContent = text
  el.body.appendChild(d)
  return d
}

function addRow(k, v) {
  const r = document.createElement('div')
  r.className = 'pn-row'
  const kk = document.createElement('div')
  kk.className = 'pn-k'
  kk.textContent = k
  const vv = document.createElement('div')
  vv.className = 'pn-v'
  vv.textContent = v
  r.append(kk, vv)
  el.body.appendChild(r)
}

export function close() {
  init()
  token += 1                     // invalidate any in-flight load
  el.root.classList.remove('on')
}

export function isOpen() {
  init()
  return el.root.classList.contains('on')
}

/**
 * Open the panel for a module/sub-item and load it.
 *
 * Every open takes a ticket. A slow request that resolves after the owner has
 * moved on must not paint its rows over the panel they are now looking at —
 * that would attribute one module's data to another, which is worse than
 * showing nothing.
 */
export async function open(moduleId, moduleLabel, item) {
  const load = panelFor(moduleId, item)
  if (!load) {
    // A sub-item with no loader is dead wiring — say so rather than spin.
    init()
    ++token
    el.title.textContent = `${moduleLabel} · ${item}`
    el.src.textContent = 'não mapeado'
    clear()
    add('pn-error', `sem leitura mapeada para ${moduleId}/${item}`)
    el.root.classList.add('on')
    return
  }
  return openCustom(`${moduleLabel} · ${item}`, load)
}

/** Same surface, for a one-off read the palette builds (a search, a recall). */
export async function openCustom(title, load) {
  init()
  const mine = ++token

  el.title.textContent = title
  el.src.textContent = ''
  clear()
  add('pn-load', 'Lendo o kernel…')
  el.root.classList.add('on')

  try {
    const out = await load()
    if (mine !== token) return
    clear()

    if (out.absent) {
      el.src.textContent = 'não existe aqui'
      add('pn-absent', out.absent)
      return
    }

    const rows = out.rows ?? []
    for (const { k, v } of rows) addRow(k, v)
    if (!rows.length && !out.note) add('pn-note', 'o kernel respondeu, e não há nada a listar')
    if (out.note) add('pn-note', out.note)
    el.src.textContent = rows.length ? `${rows.length} leitura${rows.length > 1 ? 's' : ''}` : 'vazio'
  } catch (e) {
    if (mine !== token) return
    clear()
    el.src.textContent = 'falhou'
    add('pn-error', e.human ?? String(e.message ?? e))
  }
}

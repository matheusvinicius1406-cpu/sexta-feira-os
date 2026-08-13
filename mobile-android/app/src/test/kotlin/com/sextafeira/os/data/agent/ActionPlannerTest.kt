package com.sextafeira.os.data.agent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for the pure decision logic of the agent's HANDS.
 *
 * These prove the safety vocabulary holds: it dials (never calls), composes
 * (never sends), navigates (never drives). All without touching Android.
 */
class ActionPlannerTest {

    // ── open_app ───────────────────────────────────────────

    @Test
    fun `open_app by package`() {
        val p = ActionPlanner.plan("open_app", mapOf("package" to "com.whatsapp"))
        assertEquals(ActionKind.OPEN_APP, p.kind)
        assertEquals("com.whatsapp", p.target)
        assertEquals("done", p.status)
    }

    @Test
    fun `open_app synonyms and param aliases`() {
        for (action in listOf("open_app", "abrir_app", "abrir")) {
            val p = ActionPlanner.plan(action, mapOf("app" to "whatsapp"))
            assertEquals(ActionKind.OPEN_APP, p.kind)
            assertEquals("whatsapp", p.target)
        }
        val byNome = ActionPlanner.plan("abrir", mapOf("nome" to "spotify"))
        assertEquals("spotify", byNome.target)
    }

    @Test
    fun `open_app without target fails`() {
        val p = ActionPlanner.plan("open_app", mapOf())
        assertEquals("failed", p.status)
        assertTrue(p.error!!.contains("sem 'app'/'package'"))
    }

    // ── navigate ───────────────────────────────────────────

    @Test
    fun `navigate by destination`() {
        val p = ActionPlanner.plan("navegar", mapOf("destino" to "Faculdade XYZ"))
        assertEquals(ActionKind.NAVIGATE, p.kind)
        assertEquals("Faculdade XYZ", p.target)
    }

    @Test
    fun `navigate by coordinates`() {
        val p = ActionPlanner.plan("navigate", mapOf("lat" to "-23.5", "lon" to "-46.6"))
        assertEquals("-23.5,-46.6", p.target)
    }

    @Test
    fun `navigate without destination fails`() {
        val p = ActionPlanner.plan("navigate", mapOf("lat" to "-23.5")) // lon missing
        assertEquals("failed", p.status)
        assertTrue(p.error!!.contains("destination"))
    }

    // ── dial — SAFETY: ACTION_DIAL, not CALL ──────────────

    @Test
    fun `dial normalizes phone number and strips garbage`() {
        val p = ActionPlanner.plan("ligar", mapOf("phone" to "(11) 99999-0000"))
        assertEquals(ActionKind.DIAL, p.kind)
        assertEquals("11999990000", p.target) // digits only — the safe dialer format
    }

    @Test
    fun `dial keeps plus and star for international and extensions`() {
        val p = ActionPlanner.plan("call", mapOf("number" to "+55 11 99999-0000"))
        assertEquals("+5511999990000", p.target)
    }

    @Test
    fun `dial without number fails`() {
        val p = ActionPlanner.plan("discar", mapOf())
        assertEquals("failed", p.status)
        assertTrue(p.error!!.contains("number"))
    }

    // ── sms — SAFETY: composes, never sends ───────────────

    @Test
    fun `sms composes with recipient and body`() {
        val p = ActionPlanner.plan("send_sms", mapOf("numero" to "11999990000", "mensagem" to "Te vejo lá"))
        assertEquals(ActionKind.SMS, p.kind)
        assertEquals("11999990000", p.target)
        assertEquals("Te vejo lá", p.text)
    }

    @Test
    fun `sms with only body still composes`() {
        val p = ActionPlanner.plan("sms", mapOf("text" to "lembrete"))
        assertEquals(ActionKind.SMS, p.kind)
        assertEquals("", p.target)
        assertEquals("lembrete", p.text)
    }

    @Test
    fun `sms with nothing fails`() {
        val p = ActionPlanner.plan("message", mapOf())
        assertEquals("failed", p.status)
    }

    // ── notify / toast ─────────────────────────────────────

    @Test
    fun `notify defaults title`() {
        val p = ActionPlanner.plan("notificar", mapOf("body" to "algo importante"))
        assertEquals(ActionKind.NOTIFY, p.kind)
        assertEquals("Sexta-Feira", p.title)
        assertEquals("algo importante", p.text)
    }

    @Test
    fun `notify carries command id for dedup`() {
        val p = ActionPlanner.plan("notify", mapOf("titulo" to "T", "mensagem" to "M", "id" to "cmd-1"))
        assertEquals("cmd-1", p.id)
    }

    @Test
    fun `toast defaults text`() {
        val p = ActionPlanner.plan("toast", mapOf())
        assertEquals(ActionKind.TOAST, p.kind)
        assertEquals("ok", p.text)
    }

    // ── unknown actions fail closed ────────────────────────

    @Test
    fun `unknown action fails`() {
        val p = ActionPlanner.plan("hack_the_planet", mapOf())
        assertEquals("failed", p.status)
        assertTrue(p.error!!.contains("hack_the_planet"))
    }

    @Test
    fun `case insensitive actions`() {
        assertEquals(ActionKind.OPEN_APP, ActionPlanner.plan("OPEN_APP", mapOf("app" to "x")).kind)
        assertEquals(ActionKind.DIAL, ActionPlanner.plan("Ligar", mapOf("number" to "1")).kind)
    }
}

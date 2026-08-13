package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.GraphEdge
import com.sextafeira.os.data.api.GraphNode
import com.sextafeira.os.data.api.SextaFeiraApi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt
import javax.inject.Inject

// ── Data classes for layout ──────────────────────────────

data class LayoutNode(
    val id: String,
    val title: String,
    val kind: String,
    val importance: Double,
    var x: Float,
    var y: Float,
    val radius: Float = 28f,
)

data class LayoutEdge(
    val source: String,
    val target: String,
    val relation: String,
    val weight: Double,
)

data class GraphUiState(
    val nodes: List<LayoutNode> = emptyList(),
    val edges: List<LayoutEdge> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val selectedNodeId: String? = null,
    val totalNodes: Int = 0,
    val totalEdges: Int = 0,
)

// ── ViewModel ─────────────────────────────────────────────

@HiltViewModel
class MemoryGraphViewModel @Inject constructor(
    private val api: SextaFeiraApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(GraphUiState())
    val uiState: StateFlow<GraphUiState> = _uiState.asStateFlow()

    init {
        loadGraph()
    }

    fun loadGraph() {
        _uiState.update { it.copy(isLoading = true, error = null, selectedNodeId = null) }

        viewModelScope.launch {
            try {
                val graph = api.memoryGraph(limit = 300)
                val layoutNodes = graph.nodes.map { n ->
                    LayoutNode(
                        id = n.id,
                        title = n.title ?: "sem título",
                        kind = n.kind,
                        importance = n.importance,
                        x = 0f,
                        y = 0f,
                    )
                }
                val layoutEdges = graph.edges.filter { e ->
                    layoutNodes.any { it.id == e.source } &&
                    layoutNodes.any { it.id == e.target }
                }.map { e ->
                    LayoutEdge(
                        source = e.source,
                        target = e.target,
                        relation = e.relation,
                        weight = e.weight,
                    )
                }

                // Run force-directed layout
                val positioned = forceDirectedLayout(layoutNodes, layoutEdges)

                _uiState.update {
                    it.copy(
                        nodes = positioned,
                        edges = layoutEdges,
                        isLoading = false,
                        totalNodes = positioned.size,
                        totalEdges = layoutEdges.size,
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = "Falha ao carregar grafo: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    fun selectNode(nodeId: String?) {
        _uiState.update { it.copy(selectedNodeId = nodeId) }
    }

    // ── Force-Directed Layout ────────────────────────────

    private fun forceDirectedLayout(
        nodes: List<LayoutNode>,
        edges: List<LayoutEdge>,
        width: Float = 1000f,
        height: Float = 1000f,
        iterations: Int = 100,
    ): List<LayoutNode> {
        if (nodes.isEmpty()) return nodes
        if (nodes.size == 1) {
            return nodes.map { it.copy(x = width / 2, y = height / 2) }
        }

        val result = nodes.map { it.copy() }.toMutableList()

        // Initialize positions in a circle
        val angleStep = 2.0 * PI / result.size
        val radius = min(width, height) * 0.35f
        result.forEachIndexed { i, node ->
            val angle = i * angleStep
            node.x = (width / 2 + radius * cos(angle).toFloat())
            node.y = (height / 2 + radius * sin(angle).toFloat())
        }

        val k = sqrt(width * height / result.size).coerceAtLeast(50f)
        val repulsionStrength = k * k
        val attractionStrength = 0.01f
        val damping = 0.85f
        val minMovement = 0.5f
        val centerGravity = 0.001f

        // Build adjacency set for quick lookup
        val adjacency = mutableMapOf<String, MutableSet<String>>()
        edges.forEach { e ->
            adjacency.getOrPut(e.source) { mutableSetOf() }.add(e.target)
            adjacency.getOrPut(e.target) { mutableSetOf() }.add(e.source)
        }

        for (iter in 0 until iterations) {
            val forces = MutableList(result.size) { Pair(0f, 0f) }

            // Repulsion between all pairs
            for (i in result.indices) {
                for (j in i + 1 until result.size) {
                    val dx = result[i].x - result[j].x
                    val dy = result[i].y - result[j].y
                    val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)
                    val force = repulsionStrength / (dist * dist)
                    val fx = force * dx / dist
                    val fy = force * dy / dist
                    forces[i] = Pair(forces[i].first + fx, forces[i].second + fy)
                    forces[j] = Pair(forces[j].first - fx, forces[j].second - fy)
                }
            }

            // Attraction along edges
            for (e in edges) {
                val si = result.indexOfFirst { it.id == e.source }
                val ti = result.indexOfFirst { it.id == e.target }
                if (si < 0 || ti < 0) continue

                val dx = result[ti].x - result[si].x
                val dy = result[ti].y - result[si].y
                val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)
                val force = attractionStrength * (dist * dist / k)
                val fx = force * dx / dist
                val fy = force * dy / dist
                forces[si] = Pair(forces[si].first + fx, forces[si].second + fy)
                forces[ti] = Pair(forces[ti].first - fx, forces[ti].second - fy)
            }

            // Center gravity
            result.forEachIndexed { i, node ->
                val dx = width / 2 - node.x
                val dy = height / 2 - node.y
                forces[i] = Pair(
                    forces[i].first + dx * centerGravity,
                    forces[i].second + dy * centerGravity,
                )
            }

            // Apply forces with damping
            var maxMovement = 0f
            result.forEachIndexed { i, node ->
                node.x += forces[i].first * damping
                node.y += forces[i].second * damping
                val movement = sqrt(
                    forces[i].first * forces[i].first +
                    forces[i].second * forces[i].second
                )
                maxMovement = max(maxMovement, movement * damping)
            }

            if (maxMovement < minMovement && iter > 10) break
        }

        // Normalize to fit in canvas
        val minX = result.minOf { it.x }
        val maxX = result.maxOf { it.x }
        val minY = result.minOf { it.y }
        val maxY = result.maxOf { it.y }

        val rangeX = (maxX - minX).coerceAtLeast(1f)
        val rangeY = (maxY - minY).coerceAtLeast(1f)
        val scale = min(width * 0.8f / rangeX, height * 0.8f / rangeY)
        val centerX = (minX + maxX) / 2
        val centerY = (minY + maxY) / 2

        result.forEach { node ->
            node.x = width / 2 + (node.x - centerX) * scale / 1.5f
            node.y = height / 2 + (node.y - centerY) * scale / 1.5f
        }

        return result
    }
}

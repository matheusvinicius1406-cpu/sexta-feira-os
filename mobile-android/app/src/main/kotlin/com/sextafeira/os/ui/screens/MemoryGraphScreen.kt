@file:OptIn(ExperimentalMaterial3Api::class)

package com.sextafeira.os.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material.icons.filled.ZoomOut
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.collectAsState
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.sextafeira.os.viewmodel.GraphUiState
import com.sextafeira.os.viewmodel.LayoutEdge
import com.sextafeira.os.viewmodel.LayoutNode
import com.sextafeira.os.viewmodel.MemoryGraphViewModel
import kotlin.math.sqrt

// Cached paints for Canvas rendering (allocated once, not per frame)
private val nodeLabelPaint = android.graphics.Paint().apply {
    color = android.graphics.Color.WHITE
    textSize = 13f
    textAlign = android.graphics.Paint.Align.CENTER
    isAntiAlias = true
}

private val nodeLabelPaintSmall = android.graphics.Paint().apply {
    color = android.graphics.Color.WHITE
    textSize = 11f
    textAlign = android.graphics.Paint.Align.CENTER
    isAntiAlias = true
}

private val edgeLabelPaint = android.graphics.Paint().apply {
    color = android.graphics.Color.argb(180, 180, 180, 180)
    textSize = 20f
    textAlign = android.graphics.Paint.Align.CENTER
    isAntiAlias = true
}

@Composable
fun MemoryGraphScreen(
    navController: NavHostController,
    viewModel: MemoryGraphViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    var scale by remember { mutableFloatStateOf(1f) }
    var offsetX by remember { mutableFloatStateOf(0f) }
    var offsetY by remember { mutableFloatStateOf(0f) }

    // Pinch-to-zoom and pan
    val transformableState = rememberTransformableState { zoomChange, panChange, _ ->
        scale = (scale * zoomChange).coerceIn(0.3f, 3f)
        offsetX += panChange.x
        offsetY += panChange.y
    }

    Column(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        // ── Top Bar ──────────────────────────────────────
        TopAppBar(
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(22.dp),
                    )
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text("Grafo de Memória", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        if (!uiState.isLoading) {
                            Text(
                                "${uiState.totalNodes} nós · ${uiState.totalEdges} arestas",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            },
            navigationIcon = {
                IconButton(onClick = { navController.popBackStack() }) {
                    Icon(Icons.Filled.ArrowBack, "Voltar", tint = MaterialTheme.colorScheme.primary)
                }
            },
            actions = {
                IconButton(onClick = { viewModel.loadGraph() }) {
                    Icon(Icons.Filled.Refresh, "Recarregar", tint = MaterialTheme.colorScheme.primary)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
        )

        // ── Loading ──────────────────────────────────────
        if (uiState.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(Modifier.size(36.dp))
                    Spacer(Modifier.height(12.dp))
                    Text("Calculando layout...", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
                }
            }
            return
        }

        // ── Error ────────────────────────────────────────
        if (uiState.error != null) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(uiState.error ?: "", color = MaterialTheme.colorScheme.error, fontSize = 14.sp)
                    Spacer(Modifier.height(12.dp))
                    Button(onClick = { viewModel.loadGraph() }) {
                        Text("Tentar novamente")
                    }
                }
            }
            return
        }

        // ── Empty ────────────────────────────────────────
        if (uiState.nodes.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Nenhum nó no grafo", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return
        }

        // Cores capturadas fora do DrawScope — MaterialTheme não pode ser lido dentro do onDraw.
        val primaryEdgeColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f)
        val normalEdgeColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.15f)

        // ── Graph Canvas ─────────────────────────────────
        Box(modifier = Modifier.weight(1f)) {
            Canvas(
                modifier = Modifier
                    .fillMaxSize()
                    .transformable(state = transformableState)
                    .pointerInput(uiState.nodes) {
                        detectTapGestures { tapOffset ->
                            // Transform tap to graph coordinates
                            val cx = size.width / 2f
                            val cy = size.height / 2f
                            val tx = (tapOffset.x - cx - offsetX) / scale + cx
                            val ty = (tapOffset.y - cy - offsetY) / scale + cy

                            val tapped = uiState.nodes.firstOrNull { n ->
                                val dx = n.x - tx
                                val dy = n.y - ty
                                sqrt(dx * dx + dy * dy) <= n.radius + 8f
                            }
                            viewModel.selectNode(tapped?.id)
                        }
                    },
            ) {
                val cx = size.width / 2f
                val cy = size.height / 2f

                // Apply transform
                drawContext.transform.translate(
                    offsetX + cx * (1 - scale),
                    offsetY + cy * (1 - scale),
                )
                drawContext.transform.scale(scale, scale, androidx.compose.ui.geometry.Offset(cx, cy))

                val selectedId = uiState.selectedNodeId

                // Draw edges
                uiState.edges.forEach { edge ->
                    val source = uiState.nodes.firstOrNull { it.id == edge.source }
                    val target = uiState.nodes.firstOrNull { it.id == edge.target }
                    if (source != null && target != null) {
                        val isConnectedToSelected = selectedId != null &&
                            (edge.source == selectedId || edge.target == selectedId)
                        val color = if (isConnectedToSelected)
                            primaryEdgeColor
                        else
                            normalEdgeColor

                        drawLine(
                            color = color,
                            start = Offset(source.x, source.y),
                            end = Offset(target.x, target.y),
                            strokeWidth = (edge.weight * 3f).toFloat().coerceAtLeast(0.5f),
                        )

                        // Draw relation label at midpoint
                        val midX = (source.x + target.x) / 2
                        val midY = (source.y + target.y) / 2
                        if (isConnectedToSelected && edge.relation != "related") {
                            drawContext.canvas.nativeCanvas.drawText(
                                edge.relation,
                                midX,
                                midY - 6f,
                                edgeLabelPaint,
                            )
                        }
                    }
                }

                // Draw nodes
                uiState.nodes.forEach { node ->
                    val isSelected = node.id == selectedId
                    val isConnected = selectedId != null && uiState.edges.any {
                        (it.source == selectedId && it.target == node.id) ||
                        (it.source == node.id && it.target == selectedId)
                    }
                    val highlight = isSelected || (isConnected && !isSelected)

                    drawNode(node, highlight, isSelected)
                }
            }

            // ── Zoom controls overlay ────────────────────
            Column(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilledTonalButton(
                    onClick = { scale = (scale * 1.3f).coerceAtMost(3f) },
                    modifier = Modifier.size(40.dp),
                    shape = CircleShape,
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                ) {
                    Icon(Icons.Filled.ZoomIn, "Ampliar", modifier = Modifier.size(20.dp))
                }
                FilledTonalButton(
                    onClick = { scale = (scale / 1.3f).coerceAtLeast(0.3f) },
                    modifier = Modifier.size(40.dp),
                    shape = CircleShape,
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                ) {
                    Icon(Icons.Filled.ZoomOut, "Reduzir", modifier = Modifier.size(20.dp))
                }
                FilledTonalButton(
                    onClick = {
                        scale = 1f
                        offsetX = 0f
                        offsetY = 0f
                    },
                    modifier = Modifier.size(40.dp),
                    shape = CircleShape,
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                ) {
                    Text("R", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
            }

            // ── Legend ───────────────────────────────────
            Card(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(12.dp),
                shape = RoundedCornerShape(10.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                ),
            ) {
                Column(modifier = Modifier.padding(8.dp)) {
                    Text("Legenda", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    LegendItem("Fato", kindColor("fact"))
                    LegendItem("Preferência", kindColor("preference"))
                    LegendItem("Conceito", kindColor("concept"))
                    LegendItem("Pessoa", kindColor("person"))
                    LegendItem("Projeto", kindColor("project"))
                }
            }
        }

        // ── Selected Node Detail Panel ───────────────────
        AnimatedVisibility(
            visible = uiState.selectedNodeId != null,
            enter = fadeIn() + expandVertically(expandFrom = Alignment.Bottom),
            exit = fadeOut() + shrinkVertically(shrinkTowards = Alignment.Bottom),
        ) {
            SelectedNodePanel(
                node = uiState.nodes.firstOrNull { it.id == uiState.selectedNodeId },
                nodeCount = uiState.totalNodes,
                onClose = { viewModel.selectNode(null) },
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Drawing helpers
// ═══════════════════════════════════════════════════════════

private fun DrawScope.drawNode(
    node: LayoutNode,
    highlight: Boolean,
    isSelected: Boolean,
) {
    val color = kindColor(node.kind)
    val radius = if (isSelected) node.radius * 1.4f
                 else if (highlight) node.radius * 1.15f
                 else node.radius

    // Outer glow for selected/highlighted
    if (isSelected) {
        drawCircle(
            color = color.copy(alpha = 0.2f),
            radius = radius * 1.6f,
            center = Offset(node.x, node.y),
        )
    }

    // Node body
    drawCircle(
        color = color.copy(alpha = if (highlight) 1f else 0.75f),
        radius = radius,
        center = Offset(node.x, node.y),
    )

    // Node border
    drawCircle(
        color = color.copy(alpha = 0.5f),
        radius = radius,
        center = Offset(node.x, node.y),
        style = Stroke(width = if (isSelected) 3f else 1.5f),
    )

    // Title text
    val displayText = if (node.title.length > 10) node.title.take(9) + "…" else node.title
    drawContext.canvas.nativeCanvas.drawText(
        displayText,
        node.x,
        node.y + 4f,
        if (isSelected) nodeLabelPaint else nodeLabelPaintSmall,
    )
}

@Composable
private fun LegendItem(label: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .background(color, CircleShape)
        )
        Spacer(Modifier.width(6.dp))
        Text(label, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SelectedNodePanel(
    node: LayoutNode?,
    nodeCount: Int,
    onClose: () -> Unit,
) {
    if (node == null) return

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .background(kindColor(node.kind), CircleShape),
                )
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        node.title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            node.kind,
                            fontSize = 12.sp,
                            color = kindColor(node.kind),
                            fontWeight = FontWeight.Medium,
                        )
                        Text(
                            " · importância ${(node.importance * 100).toInt()}%",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                IconButton(onClick = onClose) {
                    Icon(Icons.Filled.Close, "Fechar", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

// ── Color Helper ──────────────────────────────────────────

private fun kindColor(kind: String): Color {
    return when (kind.lowercase()) {
        "fact" -> Color(0xFF00BCD4)
        "preference" -> Color(0xFFFF6D00)
        "concept" -> Color(0xFF7C4DFF)
        "person" -> Color(0xFF4CAF50)
        "project" -> Color(0xFFE91E63)
        "note" -> Color(0xFF9E9E9E)
        else -> Color(0xFF00BCD4)
    }
}

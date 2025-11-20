/*
 1. Captura los trazos del usuario
 2. Genera una imagen (UIImage) del dibujo
 3. Permite limpiar el lienzo
 Detectar cuando hay un trazo nuevo
 */


import Foundation
import SwiftUI
import PencilKit

struct CanvasView: UIViewRepresentable {
    @Binding var canvasView: PKCanvasView

    func makeUIView(context: Context) -> PKCanvasView {
        canvasView.drawingPolicy = .anyInput
        canvasView.tool = PKInkingTool(.pen, color: .black, width: 20)
        
        canvasView.backgroundColor = .white
        

        return canvasView
    }

    
    
    func updateUIView(_ uiView: PKCanvasView, context: Context) {}
}

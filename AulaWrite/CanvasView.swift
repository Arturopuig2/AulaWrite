//
//  CanvasView.swift
//  AulaWrite
//
//  Created by ARTURO on 15/11/25.
//

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

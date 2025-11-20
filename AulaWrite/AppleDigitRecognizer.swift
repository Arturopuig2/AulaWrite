/*Es una clase en Swift que:
1.    Carga el modelo CoreML (MNISTClassifier.mlmodel // .mlpackage)
2.    Convierte la imagen escrita por el niño en un formato que el modelo pueda entender (28 x 28)
3.    Hace la predicción (¿es un 4? ¿un 7? ¿un 9?)
4.    Devuelve el dígito como String para mostrarlo en pantalla
      Es el cerebro. La IA que reconoce el dígito.
 No dibuja nada. (quien dibuja es DigitalRecognizerView.swift)
*/


import Foundation
import CoreML
import UIKit

// Clase que envuelve el modelo de Apple
final class AppleDigitRecognizer {
    static let shared = AppleDigitRecognizer()
    
    private let model: MNISTClassifier  // nombre del .mlmodel

    private init() {
        let config = MLModelConfiguration()
        do {
            self.model = try MNISTClassifier(configuration: config)
        } catch {
            fatalError("❌ No se pudo cargar MNISTClassifier: \(error)")
        }
    }
    
    func predictDigit(from image: UIImage) -> String? {
        // Redimensionamos a 28x28 y lo convertimos a CVPixelBuffer
        guard let resized = image.resized(to: CGSize(width: 28, height: 28)),
              let pixelBuffer = resized.pixelBuffer(width: 28, height: 28) else {
            print("❌ No se pudo crear pixelBuffer")
            return nil
        }
        
        // Predicción con el modelo de Apple
        guard let output = try? model.prediction(image: pixelBuffer) else {
            print("❌ Error en la predicción del modelo")
            return nil
        }
        
        // 🔵 CORRECCIÓN IMPORTANTE → convertir Int64 a String
        return String(output.classLabel)
    }
}

// MARK: - Extensiones de ayuda

extension UIImage {
    /// Redimensiona la imagen a un tamaño dado
    func resized(to size: CGSize) -> UIImage? {
        UIGraphicsBeginImageContextWithOptions(size, true, 1.0)
        defer { UIGraphicsEndImageContext() }
        draw(in: CGRect(origin: .zero, size: size))
        return UIGraphicsGetImageFromCurrentImageContext()
    }
    
    /// Convierte la imagen a un CVPixelBuffer escala de grises 8 bits
    func pixelBuffer(width: Int, height: Int, invert: Bool = true) -> CVPixelBuffer? {
        let attrs = [
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true
        ] as CFDictionary
        
        var pixelBuffer: CVPixelBuffer?
        let status = CVPixelBufferCreate(
            kCFAllocatorDefault,
            width,
            height,
            kCVPixelFormatType_OneComponent8,
            attrs,
            &pixelBuffer
        )
        
        guard status == kCVReturnSuccess, let pb = pixelBuffer else {
            return nil
        }
        
        CVPixelBufferLockBaseAddress(pb, [])
        defer { CVPixelBufferUnlockBaseAddress(pb, []) }
        
        guard let context = CGContext(
            data: CVPixelBufferGetBaseAddress(pb),
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(pb),
            space: CGColorSpaceCreateDeviceGray(),
            bitmapInfo: CGImageAlphaInfo.none.rawValue
        ) else {
            return nil
        }
        
        // Fondo blanco
        context.setFillColor(UIColor.white.cgColor)
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        
        // Dibujamos en gris
        guard let cgImage = self.cgImage else { return nil }
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
        
        // Invertimos valores si hace falta (lo ideal para MNIST)
        if invert {
            let height = CVPixelBufferGetHeight(pb)
            let width  = CVPixelBufferGetWidth(pb)
            let ptr = CVPixelBufferGetBaseAddress(pb)!.assumingMemoryBound(to: UInt8.self)
            
            for y in 0..<height {
                for x in 0..<width {
                    let i = y * CVPixelBufferGetBytesPerRow(pb) + x
                    ptr[i] = 255 - ptr[i]    // invertir 0↔255
                }
            }
        }
        
        return pb
    }
}

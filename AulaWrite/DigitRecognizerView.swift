/*
    Es la mano = la interfaz donde el niño escribe
     •    Es un View de SwiftUI
     •    Muestra un lienzo tipo “cuaderno”
     •    Captura lo que el niño dibuja
     •    Convierte ese dibujo en un UIImage
     •    Se lo da a AppleDigitRecognizer para que lo reconozca
 */



import SwiftUI
import PencilKit
import CoreML
import UIKit
import Combine


extension Notification.Name {
    static let clearCanvas = Notification.Name("clearCanvas")
}


struct DigitRecognizerView: View {
    @Binding var predictedDigit: String      // ← SE LO PASA LA VISTA PADRE
    
    @State private var canvasView = PKCanvasView()
    @State private var isRunning = false
    // quita aquí cualquier `@State private var predictedDigit = ""`
    
    // ⏱️ Timer que se dispara cada 4 segundos
    private let autoTimer = Timer
        .publish(every: 4.0, on: .main, in: .common)
        .autoconnect()
    
    var body: some View {
        VStack(spacing: 12) {
            ZStack{
                
                // Tu lienzo
                CanvasView(canvasView: $canvasView)
                    //.frame(width: 200, height: 200)
                    //.frame(maxWidth: .infinity, alignment: .center)
                    //.background(Color.white)
                    //.border(Color.black, width: 1)
                
                    .frame(width: 200, height: 200)
                    .offset(x:0)
                    .border(Color.black, width: 1)
                
                
                // cuando ya hay predicción, ocultamos el dibujo
                    .opacity(predictedDigit.isEmpty ? 1 : 0)
                
                // Capa 2: número reconocido en grande
                if !predictedDigit.isEmpty {
                    Text(predictedDigit)
                        .font(.system(size: 120, weight: .bold))   // grande, tipografía estándar
                        .foregroundColor(.blue)
                        .frame(width: 200, height: 200, alignment: .center)
                        .background(Color.white)
                        .border(Color.black, width: 1)

                }
            }
            
            HStack {
                Button("Borrar") {
                    clearCanvas()
                }
                Button("Reconocer") {
                    recognizeDigit()
                }
            }
            .font(.headline)
        }
        .padding()
        
        .onReceive(NotificationCenter.default.publisher(for: .clearCanvas)) { _ in
            clearCanvas()
        }
        
        //LANZADOR DE RECONOCIMIENTO
        .onReceive(autoTimer) { _ in
            // Si NO se está ejecutando ya el modelo,
            // NO hay todavía dígito reconocido
            // y HAY algo dibujado en el lienzo...
            if !isRunning,
               predictedDigit.isEmpty,
               !canvasView.drawing.bounds.isEmpty {
                
                print("⏱️ Auto-reconocer tras 4 segundos sin pulsar el botón")
                recognizeDigit()
            }
        }
}

    private func clearCanvas() {
        canvasView.drawing = PKDrawing()
        predictedDigit = ""
    }
    
    //FUNCIÓN RECONOCIMIENTO DE APPLE
    private func recognizeDigit() {
        print("🔹 Botón RECONOCER pulsado")
        isRunning = true
        
        let image = canvasToImage()   // UIImage del lienzo
        
        if let digit = AppleDigitRecognizer.shared.predictDigit(from: image) {
            DispatchQueue.main.async {
                print("✅ Predicción Apple MNIST:", digit)
                self.predictedDigit = digit
                self.isRunning = false
            }
        } else {
            DispatchQueue.main.async {
                print("❌ No se pudo reconocer el dígito")
                self.predictedDigit = ""
                self.isRunning = false
            }
        }
    }
    
    // Función: Creo el MLMultiArray y llamo al modelo_digitos
/*
    private func recognizeDigit() {
        print("🔹 Botón RECONOCER pulsado")
        isRunning = true
        
        let image = canvasToImage()
        
        guard let smallImage = resizeImage(image, to: CGSize(width: 28, height: 28)) else {
            print("❌ No se pudo redimensionar la imagen")
            isRunning = false
            return
        }
        guard let pixelArray = imageToGrayscaleArray(smallImage),
              pixelArray.count == 28 * 28 else {
            print("❌ No se pudo obtener el array de píxeles")
            isRunning = false
            return
        }
        
        do {
            let shape: [NSNumber] = [1, 28, 28, 1]
            let inputArray = try MLMultiArray(shape: shape, dataType: .float32)
            
            for y in 0..<28 {
                for x in 0..<28 {
                    let p = pixelArray[y * 28 + x]  // [0,1]
                    let index: [NSNumber] = [
                        0,
                        NSNumber(value: y),
                        NSNumber(value: x),
                        0
                    ]
                    inputArray[index] = NSNumber(value: p)
                }
            }
            
            let config = MLModelConfiguration()
            let model = try modelo_digitos(configuration: config)
            
            let input = modelo_digitosInput(image_input: inputArray)
            let output = try model.prediction(input: input)
            
            let digit = output.classLabel         // "0"..."9"
            
            DispatchQueue.main.async {
                print("✅ Predicción:", digit)
                self.predictedDigit = digit       // 👈 MANDAMOS EL VALOR A LA VISTA PADRE
                self.isRunning = false
            }
        } catch {
            print("❌ Error al ejecutar el modelo:", error)
            isRunning = false
        }
    }
    
    */
    
    private func canvasToImage() -> UIImage {
        let drawing = canvasView.drawing
        var bounds = drawing.bounds

        // Si no hay nada dibujado, devolvemos imagen vacía
        if bounds.isEmpty {
            return UIImage()
        }

        // Añadimos un pequeño margen alrededor del dibujo
        let padding: CGFloat = 10
        bounds = bounds.insetBy(dx: -padding, dy: -padding)

        // Nos aseguramos de no salirnos del lienzo
        bounds = bounds.intersection(canvasView.bounds)

        // Imagen solo de la zona donde hay trazos
        let drawingImage = drawing.image(from: bounds, scale: 1.0)

        // Hacemos un lienzo cuadrado para centrar el dígito
        let side = max(bounds.width, bounds.height)
        let squareSize = CGSize(width: side, height: side)

        let renderer = UIGraphicsImageRenderer(size: squareSize)
        let img = renderer.image { ctx in
            // Fondo blanco
            UIColor.white.setFill()
            ctx.fill(CGRect(origin: .zero, size: squareSize))

            // Dibujamos la imagen del dígito centrada en el cuadrado
            let x = (side - bounds.width) / 2
            let y = (side - bounds.height) / 2
            drawingImage.draw(in: CGRect(x: x, y: y, width: bounds.width, height: bounds.height))
        }

        return img
    }
    
    
    private func resizeImage(_ image: UIImage, to size: CGSize) -> UIImage? {
        UIGraphicsBeginImageContextWithOptions(size, true, 1.0)
        image.draw(in: CGRect(origin: .zero, size: size))
        let resized = UIGraphicsGetImageFromCurrentImageContext()
        UIGraphicsEndImageContext()
        return resized
    }
    
    private func imageToGrayscaleArray(_ image: UIImage) -> [Float]? {
        guard let cgImage = image.cgImage else { return nil }
        
        let width = Int(image.size.width)
        let height = Int(image.size.height)
        
        let colorSpace = CGColorSpaceCreateDeviceGray()
        let bytesPerPixel = 1
        let bytesPerRow = bytesPerPixel * width
        let bitsPerComponent = 8
        
        var pixels = [UInt8](repeating: 0, count: width * height)
        
        guard let context = CGContext(
            data: &pixels,
            width: width,
            height: height,
            bitsPerComponent: bitsPerComponent,
            bytesPerRow: bytesPerRow,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.none.rawValue
        ) else {
            return nil
        }
        
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
        
        // Normalizamos a [0, 1] → 0 = negro, 1 = blanco
        var result = [Float]()
        result.reserveCapacity(width * height)
        
        for i in 0..<(width * height) {
            let v = Float(pixels[i]) / 255.0
            result.append(v)
        }
        
        return result
    }
    
    
}

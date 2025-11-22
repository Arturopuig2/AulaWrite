/*
 La clase OperationView es la pantalla principal donde el alumno hace las
 operaciones y escribe el resultado.
 Es, en realidad, el corazón interactivo de tu app de Aula Write.

 */

import SwiftUI

struct OperationView: View {
    
    let operationType: OperationType   // 👈 viene de fuera

    @State private var n1: Int = 2
    @State private var n2: Int = 2
    
    @State private var predictedDigit: String = ""
    @State private var feedback: String = ""
    @State private var isCorrect: Bool? = nil   // nil = aún sin corregir

    
    var correctResult: Int {
        switch operationType {
        case .suma: return n1 + n2
        case .resta: return n1 - n2
        case .multiplicacion: return n1 * n2
        }
    }
    
    
    var body: some View {
        ZStack {
            Image("papel")
                .resizable()
                .scaledToFill()
                .ignoresSafeArea()
                .opacity(0.35)              // 👈 Ajusta transparencia aquí
                .allowsHitTesting(false)   // 👈 MUY IMPORTANTE

            VStack(spacing: 30) {
                // Operación en vertical
                VStack(alignment: .trailing, spacing: 8) {
                    
                    
                    Text("\(n1)")
                        .font(.system(size: 120, weight: .bold, design: .monospaced))
                    
                    Text("\(operationType.symbol) \(n2)")
                        .font(.system(size: 120, weight: .bold, design: .monospaced))

                    Rectangle()
                        .frame(width: 120, height: 8)
                }
                .frame(maxWidth: .infinity, alignment: .center)   // ← centra el bloque completo
                .offset(x: -50)
                
                // Lienzo para escribir el resultado
                DigitRecognizerView(predictedDigit: $predictedDigit)
                    .frame(width: 200, height: 200)
                   // .frame(width: 28, height: 28)
                    .offset(x:10)
                    //.border(Color.black, width: 1)
                

                //PARA QUE ME MUESTRE EL NÚMERO (Y SABER SI LO ESTÁ RECONOCIENDO BIEN)
                if !predictedDigit.isEmpty {
                   // Text("He reconocido: \(predictedDigit)")
                     //   .font(.title2)
                      //  .foregroundColor(.blue)
                }

                
                
                // Botones
                HStack(spacing: 20) {
                   // Button("Comprobar") {
                     //   checkAnswer()
                    //}

                    Button(action: {
                        checkAnswer()
                    }){
                        Image(systemName: "checkmark.circle.fill")   // ← icono de Apple SF Symbols
                        .resizable()
                        .scaledToFit()
                        .frame(width: 60, height: 60)            // tamaño del botón
                        .foregroundColor(.blue)                  // color del icono
                        //.padding()
                    }
                    
                    
                   // .font(.title2)
                    
                    Button("Siguiente") {
                        nextExercise()
                        
                    }
                    .font(.title2)
                }
                
                // Feedback
                if let isCorrect = isCorrect {
                    Text(feedback)
                        .font(.title2)
                        .foregroundColor(isCorrect ? .green : .red)
                }
                
                Spacer()

                // Botón de acceso al RAG
                NavigationLink {
                    RAGChatView()
                } label: {
                    Text("RAG")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .frame(height: 70)
                        .background(Color.blue.opacity(0.15))
                        .cornerRadius(20)
                }
                .padding(.horizontal)
                .padding(.bottom, 10)
            }
            .padding(.top, 60)
            .padding(.horizontal)
        }
    }
    
    private func checkAnswer() {
        guard !predictedDigit.isEmpty else {
            feedback = "Escribe una respuesta y pulsa Reconocer"
            isCorrect = false
            return
        }
        
        guard let userInt = Int(predictedDigit) else {
            feedback = "No he entendido el número: \(predictedDigit)"
            isCorrect = false
            return
        }
        
        if userInt == correctResult {
            feedback = "✅ Correcto: \(userInt)"
            isCorrect = true
        } else {
            feedback = "❌ Incorrecto: has puesto \(userInt), era \(correctResult)"
            isCorrect = false
        }
    }
    
    //FUNCIÓN DE LAS OPERACIONES
    private func nextExercise() {
        switch operationType {
        case .suma:
            n1=Int.random(in: 0...9)
            n2=Int.random(in: 0...(9-n1)) //ASEGURA RESULDAOD <=9
        case .resta:
            n1=Int.random(in: 0...9)
            n2=Int.random(in: 0...n1)  //ASEGURA RESULTADO POSITIVO
        case .multiplicacion:
            repeat {
                n1=Int.random(in: 0...9)
                n2=Int.random(in: 0...9)
            } while n1 * n2 > 9
        }
        
        predictedDigit = ""
        feedback = ""
        isCorrect = nil
        
        // Enviar orden de “borrar el lienzo”
        NotificationCenter.default.post(name: .clearCanvas, object: nil)
    }
}

#Preview {
    NavigationStack {
        OperationView(operationType: .suma)
            .statusBarHidden(true)
    }
}


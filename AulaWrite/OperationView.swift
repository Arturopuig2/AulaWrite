import SwiftUI

struct OperationView: View {
    @State private var n1: Int = 2
    @State private var n2: Int = 2
    
    @State private var predictedDigit: String = ""
    @State private var feedback: String = ""
    @State private var isCorrect: Bool? = nil   // nil = aún sin corregir
    
    var correctResult: Int {
        n1 + n2
    }
    
    var body: some View {
        VStack(spacing: 30) {
            // Operación en vertical
            VStack(alignment: .trailing, spacing: 8) {
                Text("\(n1)")
                    .font(.system(size: 120, weight: .bold, design: .monospaced))
                    //.frame(maxWidth: .infinity, alignment: .trailing)
                
                Text("+ \(n2)")
                    .font(.system(size: 120, weight: .bold, design: .monospaced))
                    //.frame(maxWidth: .infinity, alignment: .trailing)

                Rectangle()
                    .frame(width: 120, height: 8)
                    //.frame(maxWidth: .infinity, alignment: .center)
            }
            .frame(maxWidth: .infinity, alignment: .center)   // ← centra el bloque completo
            .offset(x: -50)
            
            // Lienzo para escribir el resultado
            DigitRecognizerView(predictedDigit: $predictedDigit)
                .frame(width: 220, height: 200)
                .offset(x:10)
            

            //PARA QUE ME MUESTRE EL NÚMERO (Y SABER SI LO ESTÁ RECONOCIENDO BIEN)
            if !predictedDigit.isEmpty {
                Text("He reconocido: \(predictedDigit)")
                    .font(.title2)
                    .foregroundColor(.blue)
            }

            // Botones
            HStack(spacing: 20) {
                Button("Comprobar") {
                    checkAnswer()
                }
                .font(.title2)
                
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
        }
        .padding(.top, 60)
        .padding(.horizontal)
        
        
        // -----------------------
        // BOTÓN DE ACCESO AL RAG EN OTRA PANTALLA
        // -----------------------
        NavigationLink {
            RAGChatView() //LS OTRA PANTALLA
        } label: {
            //Image("profesora_chat")
            Text ("RAG")
            //Label("IR AL ASISTENTE", systemImage: "bubble.left.and.bubble.right.fill")
                .font(.headline)
                //.resizable()
                .scaledToFit()
                .frame(width: 70, height: 70)
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color.blue.opacity(0.15))
                .cornerRadius(20)
        }
        .padding(.horizontal)
        
        //---------------------------------------
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
        n1 = Int.random(in: 0...9)
        n2 = Int.random(in: 0...(9 - n1))   // así n1 + n2 nunca pasa de 9
        
        predictedDigit = ""
        feedback = ""
        isCorrect = nil
        
        
        // Enviar orden de “borrar el lienzo”
        NotificationCenter.default.post(name: .clearCanvas, object: nil)
    }
}

#Preview {
    NavigationStack {
        OperationView()
    }
}

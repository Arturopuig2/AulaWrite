import SwiftUI
import AVKit

struct RAGMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
    let videoURL: URL?
}

struct RAGChatView: View {
    @State private var inputText: String = ""
    @State private var messages: [RAGMessage] = []
    @State private var isLoading: Bool = false

    private var hasTeacherResponse: Bool {
        messages.contains { !$0.isUser }
    }
    
    var body: some View {
        if !hasTeacherResponse {
            VStack {
                HStack {
                    Image("profesora_chat")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 100)      // tamaño, nada de alignment aquí
                        .frame(maxWidth: .infinity, alignment: .leading)// ESTO LA ALINEA A LA IZQUIERDA
                        .padding(.leading, 50)
                        .padding(.top, -40)
                }
                // Tu contenido debajo
                Text("")
            }
        }
        
        VStack {
            // 🟦 ZONA DE MENSAJES CON SCROLL
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(messages) { msg in
                        HStack {
                            if msg.isUser { Spacer() }
                            
                            VStack(
                                alignment: msg.isUser ? .trailing : .leading,
                                spacing: 8
                            ) {
                                // 💬 BURBUJA DE TEXTO
                                Text(msg.text)
                                    .font(.system(size: 26))
                                    .padding(10)
                                    .background(msg.isUser ? Color.blue.opacity(0.2) : Color.white.opacity(0))
                                    .cornerRadius(12)
                                    // 👇 ancho máximo relativo, sin UIScreen.main
                                    .frame(maxWidth: .infinity,
                                           alignment: msg.isUser ? .trailing : .leading)
                                
                                // 🎥 VÍDEO DEBAJO DEL TEXTO (solo RAG)
                                if let videoURL = msg.videoURL, !msg.isUser {
                                    VideoPlayer(player: AVPlayer(url: videoURL))
                                        .frame(height: 220)
                                        .cornerRadius(12)
                                        .shadow(radius: 4)
                                }
                            }
                            .padding(.horizontal, 40) // limita el ancho real de la burbuja
                            
                            if !msg.isUser { Spacer() }
                        }
                    }
                }
                .padding(.vertical)
            }
            
            Divider()
            
            // 🟧 ZONA DE ENTRADA
            HStack {
               // TextField("Escribe tu pregunta…", text: $inputText, axis: .vertical)
                 //   .textFieldStyle(.roundedBorder)
                   // .lineLimit(1...3)
                               
                    
                    ZStack(alignment: .topLeading) {
                        if inputText.isEmpty {
                            Text("Aquí tu pregunta…")
                                .foregroundColor(.red)
                                .font(.system(size: 26))
                                .padding(.vertical, 16)
                                .padding(.horizontal, 16)
                        }

                        TextEditor(text: $inputText)
                            .frame(height: 100)
                            .padding(8)
                            .background(Color.blue.opacity(0.4))
                            .cornerRadius(14)
                            .font(.system(size: 26))
                    }
                
                if isLoading {
                    ProgressView()
                        .padding(.horizontal, 4)
                } else {
                    Button {
                        sendMessage()
                    } label: {
                        Image(systemName: "paperplane.fill")
                            .font(.largeTitle.bold().pointSize(40))
                    }
                    .disabled(inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .padding()
        }
        .toolbar {
            if !hasTeacherResponse {
                ToolbarItem(placement: .principal) {
                    Text("Hola, ¿en qué puedo ayudarte?")
                        .font(.system(size: 28))
                        .foregroundColor(.blue)
                }
            }
        }
        
        VStack {
            HStack {
                Spacer()
                // empuja la imagen a la derecha
                //Image("profesora_chat")          // nombre en Assets.xcassets
                  //  .resizable()
                    //.scaledToFit()
                    .frame(width: 80, height: 80)
                    //.padding(.trailing, 20)
                    //.padding(.top, 20)
            }

            // Tu contenido debajo
            Text("")
        }
        
    }
    
    private func sendMessage() {
        let question = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !question.isEmpty else { return }
        
        messages.append(RAGMessage(text: question, isUser: true, videoURL: nil))
        inputText = ""
        isLoading = true
        
        Task {
            do {
                let result = try await RAGService.ask(question)
                
                await MainActor.run {
                    messages.append(
                        RAGMessage(
                            text: result.answer,
                            isUser: false,
                            videoURL: result.videoURL
                        )
                    )
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    messages.append(
                        RAGMessage(
                            text: "Error al conectar con el servidor RAG.",
                            isUser: false,
                            videoURL: nil
                        )
                    )
                    isLoading = false
                }
            }
        }
    }
}


// Vista de preview (solo para ver en el canvas de Xcode)
struct RAGChatView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationStack {
            RAGChatView()
        }
    }
}

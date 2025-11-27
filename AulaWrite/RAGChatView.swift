import SwiftUI
import AVKit
import AVFoundation
import Foundation

struct RAGMessage: Identifiable {
    let id = UUID()
    var text: String
    var isUser: Bool
    var videoURL: URL?
    var audioURL: URL?
}

struct RAGChatView: View {
    @State private var inputText: String = ""
    @State private var messages: [RAGMessage] = []
    @State private var isLoading: Bool = false
    @State private var audioPlayer: AVPlayer?
    @State private var videoPlayer: AVPlayer?
    
    @State private var currentAudioURL: URL?
    @State private var isAudioPlaying: Bool = false

    private var hasTeacherResponse: Bool {
        messages.contains { !$0.isUser }
    }
    
    var body: some View {
        VStack {
            // Cabecera inicial con la profe solo si aún no hay respuesta
            if !hasTeacherResponse {
                HStack {
                    Image("profesora_chat")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 100)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.leading, 50)
                        .padding(.top, -40)
                }
            }
            
            // 🟦 ZONA DE MENSAJES CON SCROLL
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { msg in
                            HStack {
                                // Mensaje del asistente → izquierda
                                if msg.isUser { Spacer().frame(width: 0) }
                                
                                VStack(alignment: msg.isUser ? .trailing : .leading, spacing: 8) {
                                    
                                    // 💬 BURBUJA DE TEXTO
                                    Text(msg.text)
                                        .font(.system(size: 26))
                                        .padding(12)
                                        .background(
                                            msg.isUser
                                            ? Color.blue.opacity(0.20)
                                            : Color.white.opacity(0)
                                        )
                                        .cornerRadius(14)
                                        .frame(
                                            maxWidth: .infinity,         // ← ANCHO COMPLETO IPAD
                                            alignment: msg.isUser ? .trailing : .leading
                                        )
                                    
                                    // 🎧 BOTÓN DE AUDIO (play / pausa)
                                    if let audio = msg.audioURL {
                                        Button {
                                            toggleAudio(for: audio)
                                        } label: {
                                            HStack {
                                                Image(systemName: audioButtonImageName(for: audio))
                                                Text(audioButtonTitle(for: audio))
                                            }
                                            .font(.headline)
                                            .foregroundColor(.blue)
                                        }
                                    }
                                    
                                    // 🎬 VIDEO (si existe videoURL)
                                    if let video = msg.videoURL {
                                        VideoPlayer(player: AVPlayer(url: video))
                                            .frame(height: 160)
                                            .cornerRadius(12)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: msg.isUser ? .trailing : .leading)
                                
                                // Mensaje del usuario → derecha
                                if msg.isUser { Spacer().frame(width: 0) }
                            }
                            .padding(.horizontal)
                            .id(msg.id)
                        }
                    }
                }
                // Autoscroll SIN animación
                .onChange(of: messages.count) {
                    if let last = messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            
            Divider()
            
            // 🟧 ZONA DE ENTRADA
            HStack {
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
                            .font(.largeTitle)
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
    }
    
    
    private func sendMessage() {
        let question = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !question.isEmpty else { return }
        
        // Mensaje del alumno
        messages.append(
            RAGMessage(
                text: question,
                isUser: true,
                videoURL: nil,
                audioURL: nil
            )
        )
        
        inputText = ""
        isLoading = true
        
        Task {
            do {
                let result = try await RAGService.ask(question)
                
                await MainActor.run {
                    // Mensaje de la profe
                    messages.append(
                        RAGMessage(
                            text: result.answer,
                            isUser: false,
                            videoURL: result.videoURL,
                            audioURL: result.audioURL
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
                            videoURL: nil,
                            audioURL: nil
                        )
                    )
                    isLoading = false
                }
            }
        }
    }
    
    
    // MARK: - Control de audio (play / pausa)
    
    private func isPlaying(url: URL) -> Bool {
        currentAudioURL == url && isAudioPlaying
    }
    
    private func toggleAudio(for url: URL) {
        // Si ya estamos reproduciendo este mismo audio, hacemos pausa / reanudar
        if currentAudioURL == url, let player = audioPlayer {
            if player.timeControlStatus == .playing {
                player.pause()
                isAudioPlaying = false
            } else {
                player.play()
                isAudioPlaying = true
            }
        } else {
            // Es un audio nuevo: creamos player nuevo y reproducimos
            audioPlayer = AVPlayer(url: url)
            currentAudioURL = url
            audioPlayer?.play()
            isAudioPlaying = true
        }
    }
    
    private func audioButtonImageName(for url: URL) -> String {
        isPlaying(url: url) ? "pause.circle.fill" : "play.circle.fill"
    }
    
    private func audioButtonTitle(for url: URL) -> String {
        isPlaying(url: url) ? "Pausar audio" : "Escuchar respuesta"
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





















/*
Gestor global de audio que puedes llamar desde cualquier vista.
*/


import AVFoundation


final class AudioManager {
    static let shared = AudioManager()
    private var player: AVAudioPlayer?

    private init() {}

    func playSound(_ name: String, ext: String = "mp3") {
        if let url = Bundle.main.url(forResource: name, withExtension: ext) {
            do {
                player = try AVAudioPlayer(contentsOf: url)
                player?.play()
            } catch {
                print("❌ Error reproduciendo sonido:", error)
            }
        } else {
            print("❌ Archivo de sonido no encontrado:", name)
        }
    }
}

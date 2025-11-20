import Foundation

// MARK: - Modelos de respuesta

/// Ajusta este modelo a lo que devuelva tu API Python.
/// Aquí asumimos que la API responde: { "answer": "texto..." }
struct RAGResponse: Decodable {
    let answer: String
    let video_url:String?
}

// MARK: - Errores de red

enum RAGServiceError: Error {
    case invalidURL
    case invalidResponse
    case httpError(Int)
}

// MARK: - Servicio RAG

struct RAGServiceResult {
    let answer: String
    let videoURL: URL?
}

struct RAGService {
    
    /// Dirección base de tu API Python (cámbiala cuando la tengas). La dirección del servidor Python FastAPI
    /// Ejemplos:
    /// - Local de pruebas: "http://127.0.0.1:8000"
    /// - Servidor remoto: "https://mi-servidor-rag.com"
    private static let baseURLString = "http://127.0.0.1:8000"
    
    /// Ruta del endpoint que expone el RAG.
    /// En FastAPI podría ser, por ejemplo, @app.post("/ask")
    private static let endpointPath = "/ask"
    
    /// Llama al RAG con una pregunta en texto y devuelve la respuesta como String.
    static func ask(_ question: String) async throws -> RAGServiceResult {
        // 1. Construir URL
        guard let url = URL(string: baseURLString + endpointPath) else {
            throw RAGServiceError.invalidURL
        }
        
        // 2. Crear petición
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json",
                         forHTTPHeaderField: "Content-Type")
        
        // 3. Cuerpo JSON que espera tu API Python.
        //    Aquí asumimos que recibe: { "question": "..." }
        let body = ["question": question]
        request.httpBody = try JSONEncoder().encode(body)
        
        // 4. Llamada a la red
        let (data, response) = try await URLSession.shared.data(for: request)
        
        // 5. Comprobación de código HTTP
        if let httpResponse = response as? HTTPURLResponse {
            guard (200..<300).contains(httpResponse.statusCode) else {
                throw RAGServiceError.httpError(httpResponse.statusCode)
            }
        } else {
            throw RAGServiceError.invalidResponse
        }
        
        // 6. Decodificar JSON
        let decoded = try JSONDecoder().decode(RAGResponse.self, from: data)
        
        
        let fullVideoURL: URL?
        if let videoPath = decoded.video_url {
            fullVideoURL = URL(string: baseURLString + videoPath)
        } else {
            fullVideoURL = nil
        }
        
        return RAGServiceResult(answer: decoded.answer, videoURL: fullVideoURL)

    }
}

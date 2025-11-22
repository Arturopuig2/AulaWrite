/*En esta clase creo el selector de operaciones
 */

import Foundation


enum OperationType: String, CaseIterable, Identifiable {
    case suma
    case resta
    case multiplicacion

    var id: String { rawValue }

    var symbol: String {
        switch self {
        case .suma:  return "+"
        case .resta: return "−"
        case .multiplicacion: return "x"
        }
    }

    var title: String {
        switch self {
        case .suma:  return "Sumas"
        case .resta: return "Restas"
        case .multiplicacion: return "Multiplicacion"
        }
    }
}



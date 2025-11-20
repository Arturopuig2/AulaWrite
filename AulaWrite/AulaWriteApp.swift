import SwiftUI

@main
struct AulaWriteApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack{
                OperationView()    // 👈 aquí es donde empieza la app
            }
        }
    }
}

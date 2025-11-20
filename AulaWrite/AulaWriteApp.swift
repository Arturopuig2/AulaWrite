/*
 La clase AulaWriteApp.swift es el punto de entrada de la aplicación SwiftUI.
 Es decir, es la primera clase que se ejecuta cuando el usuario abre la app.
 */


import SwiftUI

@main
struct AulaWriteApp: App {
    @State private var showSplash = true
    
    var body: some Scene {
        WindowGroup {
            Group {
                if showSplash {
                    SplashView()
                        .onAppear {
                            // Tras 1.5 segundos, pasamos a la pantalla principal
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                withAnimation {
                                    showSplash = false
                                }
                            }
                        }
                } else {
                    // 👇 IMPORTANTE: OperationView dentro de NavigationStack
                    NavigationStack {
                        OperationView()  // aquí es donde empieza la app
                        .statusBarHidden(true)
                    }
                }
            }
        }
    }
}

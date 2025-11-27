import SwiftUI

struct SplashView: View {
    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()   // fondo

            VStack(spacing: 16) {
                Image("logo_aula")         // pon aquí el nombre de tu imagen en Assets
                    .resizable()
                    .scaledToFit()
                    .frame(width: 180, height: 180)

                Text("Cálculo")
                    .font(.largeTitle.bold())
                    .foregroundColor(.gray)

                Text("")
                    .font(.headline)
                    .foregroundColor(.gray)
            }
            .statusBarHidden(true)
        }
    }
}

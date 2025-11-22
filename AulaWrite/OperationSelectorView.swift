import SwiftUI

struct OperationSelectorView: View {
    var body: some View {
        NavigationStack {
            ZStack {
                // Si quieres, mismo fondo papel:
                Color(.systemBackground).ignoresSafeArea()

                VStack(spacing: 40) {
                    Text("¿Qué quieres practicar?")
                        .font(.largeTitle.bold())
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    VStack(spacing: 20) {
                        // Botón SUMAS
                        NavigationLink {
                            OperationView(operationType: .suma)
                        } label: {
                            HStack {
                                Text("➕ Sumas")
                                    .font(.title2.bold())
                                Spacer()
                                Image(systemName: "plus.circle.fill")
                                    .font(.largeTitle)
                            }
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(Color.blue.opacity(0.15))
                            .cornerRadius(20)
                        }

                        // Botón RESTAS
                        NavigationLink {
                            OperationView(operationType: .resta)
                        } label: {
                            HStack {
                                Text("➖ Restas")
                                    .font(.title2.bold())
                                Spacer()
                                Image(systemName: "minus.circle.fill")
                                    .font(.largeTitle)
                            }
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(Color.orange.opacity(0.15))
                            .cornerRadius(20)
                        }
                        
                        // Botón MULTIPLICACIONES
                        NavigationLink {
                            OperationView(operationType: .multiplicacion)
                        } label: {
                            HStack {
                                Text("✖️ Multiplicaciones")
                                    .font(.title2.bold())
                                Spacer()
                                Image(systemName: "multiply.circle.fill")
                                    .font(.largeTitle)
                            }
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(Color.green.opacity(0.15))
                            .cornerRadius(20)
                        }
                        
                    }
                    .padding(.horizontal)

                    Spacer()
                }
            }
        }
    }
}

#Preview {
    OperationSelectorView()
}

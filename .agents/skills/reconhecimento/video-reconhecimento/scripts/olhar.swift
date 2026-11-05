// olhar.swift — amostra quadros de um vídeo e mede, com o framework Vision da Apple, o rosto maior de cada quadro:
// caixa normalizada, giro da cabeça (roll/yaw/pitch) e, pelos pontos de referência, para onde os olhos apontam e
// quanto estão abertos. Não desenha nada, não usa rede e não decide nada: quem classifica é o reconhecer.py.
//
// uso: olhar <vídeo> <saida.json> [--fps 2] [--inicio S] [--fim S] [--lado 640] [--max-rostos 4]
//
// Saída: {"versao", "detector", "largura", "altura", "duracao", "fps", "falhas",
//         "amostras": [{"t", "rostos": [{"x","y","w","h","conf","roll","yaw","pitch","olho_x","olho_y","abertura"}]}]}
// olho_x/olho_y: deslocamento da pupila dentro do olho (−1 = canto interno/alto, +1 = externo/baixo; 0 = centro).
// Quadro sem rosto vira "rostos": []. Os rostos saem do maior para o menor.

import AVFoundation
import CoreGraphics
import Foundation
import Vision

func opcao(_ nome: String, _ padrao: Double) -> Double {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: nome), i + 1 < a.count, let v = Double(a[i + 1]) { return v }
    return padrao
}

func sair(_ codigo: Int32, _ mensagem: String) -> Never {
    FileHandle.standardError.write((mensagem + "\n").data(using: .utf8)!)
    exit(codigo)
}

let argumentos = CommandLine.arguments
if argumentos.count < 3 { sair(64, "uso: olhar <vídeo> <saida.json> [--fps 2] [--inicio S] [--fim S] [--lado 640] [--max-rostos 4]") }
let entrada = URL(fileURLWithPath: argumentos[1])
let saida = URL(fileURLWithPath: argumentos[2])
if !FileManager.default.fileExists(atPath: entrada.path) { sair(1, "olhar: vídeo não encontrado: \(entrada.path)") }

let asset = AVURLAsset(url: entrada)
guard let trilha = asset.tracks(withMediaType: .video).first else { sair(1, "olhar: o arquivo não tem trilha de vídeo") }
let duracao = CMTimeGetSeconds(asset.duration)
let tamanho = trilha.naturalSize.applying(trilha.preferredTransform)
let largura = abs(tamanho.width), altura = abs(tamanho.height)

let fps = max(0.2, min(10, opcao("--fps", 2)))
let inicio = max(0, opcao("--inicio", 0))
let fim = min(duracao, opcao("--fim", duracao))
let lado = max(240, opcao("--lado", 640))
let maxRostos = max(1, Int(opcao("--max-rostos", 4)))
if fim <= inicio { sair(64, "olhar: trecho vazio (--inicio \(inicio) --fim \(fim); o vídeo tem \(duracao) s)") }

let gerador = AVAssetImageGenerator(asset: asset)
gerador.appliesPreferredTrackTransform = true
gerador.maximumSize = CGSize(width: lado, height: lado)
gerador.requestedTimeToleranceBefore = CMTime(value: 1, timescale: 30)
gerador.requestedTimeToleranceAfter = CMTime(value: 1, timescale: 30)

/// Caixa (x0, y0, x1, y1) de uma região de pontos de referência, em coordenadas normalizadas do rosto.
func caixa(_ regiao: VNFaceLandmarkRegion2D?) -> (Double, Double, Double, Double)? {
    guard let r = regiao, r.pointCount > 0 else { return nil }
    var x0 = Double.infinity, y0 = Double.infinity, x1 = -Double.infinity, y1 = -Double.infinity
    for p in r.normalizedPoints {
        x0 = min(x0, Double(p.x)); x1 = max(x1, Double(p.x))
        y0 = min(y0, Double(p.y)); y1 = max(y1, Double(p.y))
    }
    return (x0, y0, x1, y1)
}

/// Centro de uma região (média dos pontos), em coordenadas normalizadas do rosto.
func centro(_ regiao: VNFaceLandmarkRegion2D?) -> (Double, Double)? {
    guard let r = regiao, r.pointCount > 0 else { return nil }
    var sx = 0.0, sy = 0.0
    for p in r.normalizedPoints { sx += Double(p.x); sy += Double(p.y) }
    return (sx / Double(r.pointCount), sy / Double(r.pointCount))
}

/// Deslocamento da pupila dentro do olho e abertura do olho (altura ÷ largura do contorno).
func olho(_ contorno: VNFaceLandmarkRegion2D?, _ pupila: VNFaceLandmarkRegion2D?) -> (Double, Double, Double)? {
    guard let c = caixa(contorno), let p = centro(pupila) else { return nil }
    let lx = max(1e-6, c.2 - c.0), ly = max(1e-6, c.3 - c.1)
    let dx = (p.0 - (c.0 + c.2) / 2) / (lx / 2)
    let dy = (p.1 - (c.1 + c.3) / 2) / (ly / 2)
    return (max(-3, min(3, dx)), max(-3, min(3, dy)), ly / lx)
}

func arred(_ v: Double, _ casas: Double = 1000) -> Double { (v * casas).rounded() / casas }

var amostras: [[String: Any]] = []
var falhas = 0, comRosto = 0, n = 0
while true {
    let t = inicio + Double(n) / fps
    if t >= fim { break }
    n += 1
    autoreleasepool {
        var achados: [[String: Any]] = []
        guard let imagem = try? gerador.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) else {
            falhas += 1
            amostras.append(["t": arred(t), "rostos": []])
            return
        }
        // Duas passadas: as CAIXAS na revisão 3 (é ela que devolve roll, yaw e pitch) e, em cima delas, os PONTOS
        // DE REFERÊNCIA (pupila e contorno do olho). A segunda passada recebe a primeira em inputFaceObservations,
        // então não redetecta nada. Saem TODOS os rostos do quadro, do maior para o menor; quem escolhe de quem é
        // o vídeo é o reconhecer.py.
        let caixas = VNDetectFaceRectanglesRequest()
        caixas.revision = VNDetectFaceRectanglesRequestRevision3
        do {
            let tratador = VNImageRequestHandler(cgImage: imagem, options: [:])
            try tratador.perform([caixas])
            let rostos = (caixas.results ?? []).sorted { $0.boundingBox.width * $0.boundingBox.height > $1.boundingBox.width * $1.boundingBox.height }
            var comPontos: [VNFaceObservation] = []
            if !rostos.isEmpty {
                let pontos = VNDetectFaceLandmarksRequest()
                pontos.revision = VNDetectFaceLandmarksRequestRevision3
                pontos.inputFaceObservations = Array(rostos.prefix(maxRostos))
                try? tratador.perform([pontos])
                comPontos = pontos.results ?? []
            }
            for (i, r0) in rostos.prefix(maxRostos).enumerated() {
                let b = r0.boundingBox                    // Vision: origem embaixo à esquerda
                var d: [String: Any] = ["x": arred(Double(b.minX)), "y": arred(Double(1 - b.maxY)),
                                        "w": arred(Double(b.width)), "h": arred(Double(b.height)),
                                        "conf": arred(Double(r0.confidence))]
                let o = i < comPontos.count ? comPontos[i] : r0
                if let r = (o.roll ?? r0.roll)?.doubleValue { d["roll"] = arred(r) }
                if let y = (o.yaw ?? r0.yaw)?.doubleValue { d["yaw"] = arred(y) }
                if let p = (o.pitch ?? r0.pitch)?.doubleValue { d["pitch"] = arred(p) }
                if let m = o.landmarks {
                    let esq = olho(m.leftEye, m.leftPupil), dir = olho(m.rightEye, m.rightPupil)
                    let xs = [esq?.0, dir?.0].compactMap { $0 }
                    let ys = [esq?.1, dir?.1].compactMap { $0 }
                    let ab = [esq?.2, dir?.2].compactMap { $0 }
                    if !xs.isEmpty { d["olho_x"] = arred(xs.reduce(0, +) / Double(xs.count)) }
                    if !ys.isEmpty { d["olho_y"] = arred(ys.reduce(0, +) / Double(ys.count)) }
                    if !ab.isEmpty { d["abertura"] = arred(ab.reduce(0, +) / Double(ab.count)) }
                    // nariz em relação ao centro do rosto: pista de giro quando o yaw não vem
                    if let nz = centro(m.nose) { d["nariz_x"] = arred(nz.0 - 0.5); d["nariz_y"] = arred(nz.1 - 0.5) }
                }
                achados.append(d)
            }
            if !achados.isEmpty { comRosto += 1 }
        } catch { falhas += 1 }
        amostras.append(["t": arred(t), "rostos": achados])
    }
}
if !amostras.isEmpty && falhas == amostras.count { sair(1, "olhar: nenhum quadro pôde ser lido ou analisado (\(falhas) falha(s))") }

let doc: [String: Any] = ["versao": 1, "detector": "Vision VNDetectFaceRectangles r3 + Landmarks r3", "largura": Double(largura),
                          "altura": Double(altura), "duracao": arred(duracao), "fps": fps, "inicio": arred(inicio),
                          "fim": arred(fim), "falhas": falhas, "amostras": amostras]
guard let dados = try? JSONSerialization.data(withJSONObject: doc, options: [.sortedKeys]) else { sair(1, "olhar: não consegui montar o JSON") }
do { try dados.write(to: saida) } catch { sair(1, "olhar: não consegui gravar \(saida.path): \(error.localizedDescription)") }
print("olhar: \(amostras.count) amostra(s) de \(arred(inicio)) a \(arred(fim)) s, \(comRosto) com rosto, \(falhas) falha(s)")

// Illustrator(.ai) · PDF 를 **투명도를 살려** PNG 로 뽑는다.
//
// 🔴 `sips` 로 바꾸면 흰 바탕이 깔려서 누끼가 죽는다. 빈 컨텍스트(clear)에
// 직접 그려야 알파가 남는다.
//
//   swift scripts/ai-to-png.swift <입력.ai|pdf> <출력.png> [가로 픽셀]

import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else {
  FileHandle.standardError.write("쓰기: swift scripts/ai-to-png.swift <입력> <출력.png> [가로]\n".data(using: .utf8)!)
  exit(64)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
let targetW = args.count > 3 ? Double(args[3]) ?? 2400 : 2400

guard let doc = CGPDFDocument(inURL as CFURL), let page = doc.page(at: 1) else {
  FileHandle.standardError.write("PDF 를 못 읽었다\n".data(using: .utf8)!)
  exit(1)
}

// 🔴 자르기 상자(CropBox)가 아니라 **MediaBox** 를 쓴다. 일러스트레이터는
// 아트보드 밖에도 내용을 남겨 두는데, 배경 사진과 자리를 맞추려면 원본
// 캔버스 전체가 필요하다.
let box = page.getBoxRect(.mediaBox)
let scale = targetW / box.width
let w = Int((box.width * scale).rounded())
let h = Int((box.height * scale).rounded())

guard
  let ctx = CGContext(
    data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
    space: CGColorSpace(name: CGColorSpace.sRGB)!,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
else { exit(2) }

// 바탕을 칠하지 않는다 — 투명한 채로 둔다.
ctx.interpolationQuality = .high
ctx.scaleBy(x: scale, y: scale)
ctx.translateBy(x: -box.origin.x, y: -box.origin.y)
ctx.drawPDFPage(page)

guard let img = ctx.makeImage(),
  let dest = CGImageDestinationCreateWithURL(outURL as CFURL, UTType.png.identifier as CFString, 1, nil)
else { exit(3) }
CGImageDestinationAddImage(dest, img, nil)
guard CGImageDestinationFinalize(dest) else { exit(4) }

print("완료: \(w)×\(h)  \(outURL.path)")

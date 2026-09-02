// 사진에서 **사람만 오려 낸** 투명 PNG 를 만든다.
//
// 🔴 왜 필요한가 — 배경 사진 위에 큰 글자를 깔되 **글자가 사람 앞으로 오면 안
// 된다**(레퍼런스: Elite Court Supplies). 그러려면 사람만 따로 떠서 글자 위에
// 다시 덮어야 한다.
//
// 영상 분석 화면은 같은 일을 SVG 필터로 한다(`#ss-shadow-cut`). 그건 홈 사진의
// 인물이 **거의 검은 실루엣**이라 밝기만으로 오려낼 수 있어서다. 레슨 · 상점
// 사진은 인물이 밝게 조명돼 있어 그 방법이 안 통한다 — 진짜 분리가 필요하다.
//
// macOS 의 Vision 이 사람 분리를 기본으로 제공하므로 내려받을 모델이 없다.
//
// ⚠️ **다만 머리카락은 못 산다.** `VNGeneratePersonSegmentation` 은 "사람이
// 있는 영역" 을 거칠게 칠하는 것이라 가장자리가 가위로 자른 것처럼 나온다.
// 화면에 크게 깔리는 그림에는 그 차이가 그대로 보이므로, 그런 자리에는
// **손으로 딴 누끼**를 쓰는 편이 낫다(레슨 · 상점의 `market_cutout.webp` 가
// 그렇게 만든 것이다 — `scripts/ai-to-png.swift` 참고). 이 도구는 급할 때나
// 작게 쓰는 그림에 맞다.
//
//   swift scripts/cutout.swift <입력> <출력.png>

import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
  FileHandle.standardError.write("쓰기: swift scripts/cutout.swift <입력> <출력.png>\n".data(using: .utf8)!)
  exit(64)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])

guard let src = CIImage(contentsOf: inURL) else {
  FileHandle.standardError.write("입력을 못 읽었다\n".data(using: .utf8)!)
  exit(1)
}

let request = VNGeneratePersonSegmentationRequest()
// 화면에 크게 깔리는 그림이라 가장자리가 곧 품질이다 — 가장 정확한 등급을 쓴다.
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8

let handler = VNImageRequestHandler(ciImage: src, options: [:])
do {
  try handler.perform([request])
} catch {
  FileHandle.standardError.write("분리 실패: \(error)\n".data(using: .utf8)!)
  exit(2)
}

guard let result = request.results?.first else {
  FileHandle.standardError.write("사람을 못 찾았다\n".data(using: .utf8)!)
  exit(3)
}

// 🔴 마스크는 원본보다 작게 나온다 — 원본 크기로 늘려야 자리가 맞는다.
var mask = CIImage(cvPixelBuffer: result.pixelBuffer)
mask = mask.transformed(
  by: CGAffineTransform(
    scaleX: src.extent.width / mask.extent.width,
    y: src.extent.height / mask.extent.height))

// 가장자리를 아주 살짝 흐려 톱니를 없앤다. 크게 흐리면 인물 둘레에 배경이
// 반투명하게 묻어 나온다.
mask = mask.applyingGaussianBlur(sigma: 0.8).cropped(to: src.extent)

guard let blend = CIFilter(name: "CIBlendWithMask") else { exit(4) }
blend.setValue(src, forKey: kCIInputImageKey)
// 배경은 **투명**이다 — 그래야 뒤의 글자가 비친다.
blend.setValue(CIImage.empty(), forKey: kCIInputBackgroundImageKey)
blend.setValue(mask, forKey: kCIInputMaskImageKey)

guard let out = blend.outputImage?.cropped(to: src.extent) else { exit(5) }

let ctx = CIContext()
do {
  try ctx.writePNGRepresentation(
    of: out, to: outURL, format: .RGBA8,
    colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
} catch {
  FileHandle.standardError.write("쓰기 실패: \(error)\n".data(using: .utf8)!)
  exit(6)
}

print("완료: \(outURL.path)")

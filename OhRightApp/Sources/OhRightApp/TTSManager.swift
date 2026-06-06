import AppKit

class TTSManager {
    static let shared = TTSManager()

    private let synthesizer = NSSpeechSynthesizer()

    private init() {}

    func speak(_ text: String) {
        synthesizer.stopSpeaking()
        synthesizer.startSpeaking(text)
    }

    func stop() {
        synthesizer.stopSpeaking()
    }
}

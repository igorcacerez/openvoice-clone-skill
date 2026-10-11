# Base feminina local em português

A opção Kokoro usa `kokoro-onnx==0.4.9`, pesos ONNX da release `model-files-v1.0` e `pf_dora`, com fonemização `pt-br`. O OpenVoice continua convertendo o timbre para o perfil cadastrado. Nenhuma referência é enviada a serviços externos.

Após a instalação principal, execute:

```powershell
python scripts/setup_kokoro.py --config "$env:APPDATA/openvoice-clone/config.json"
```

O script requer `uv`, instala um ambiente separado, verifica SHA-256 dos pesos e preserva a biblioteca. O backup da configuração permite retornar à base anterior. Os demais idiomas continuam usando Piper. A CLI registra `tts_base` no histórico e recalibra a origem ao mudar modelo ou voz base.

Para uma prévia mais calma, use `--speed 0.8`. Frases em Kokoro são processadas separadamente, com pausa de 400 ms entre elas. Velocidade e pontuação ajudam o ritmo, mas não constituem controles de emoção. Não há promessa de reprodução idêntica da referência. A transcrição automática ajuda a detectar palavras distorcidas; não comprova naturalidade, emoção ou semelhança.

Fontes: [runtime e licença MIT](https://github.com/thewh1teagle/kokoro-onnx), [modelo e licença Apache 2.0](https://huggingface.co/hexgrad/Kokoro-82M). Pesos baixados da release do autor; não distribuídos neste repositório.

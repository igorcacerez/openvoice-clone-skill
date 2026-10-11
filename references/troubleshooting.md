# Solução de problemas

## Python ou dependências

Use o executável da `.venv` do runtime. Python 3.14 não é o runtime validado. O código upstream fixa NumPy 1.22 e vários pacotes legados em `setup.py`; esta aplicação importa a revisão fixada diretamente e instala o subconjunto necessário ao conversor com versões testadas. Não execute `pip install -e repo` por cima deste ambiente, pois isso reinstala os requisitos antigos.

`uv pip check --python CAMINHO_PYTHON` verifica consistência. O ambiente Piper é separado para evitar conflitos e executa o motor pelo processo externo. Verifique a integridade dos arquivos ONNX/config se Piper falhar. No primeiro processamento, imports e caches locais podem demorar mais; não encerre apenas porque não houve saída imediata.

## CUDA e memória

`doctor --load-models` deve mostrar a GPU e carregar o conversor. Se CUDA falhar, tente `OPENVOICE_DEVICE=cpu` e repita. Se faltar VRAM durante uma narração, reduza `--max-chars` ou use CPU. Não instale nem troque drivers globais automaticamente. O runtime CUDA 11.8 vem no wheel PyTorch.

## Checkpoints

Downloads são do Hugging Face oficial e fixados em revisão. Um download interrompido usa extensão `.download`; repita setup_models. Checksum diferente é recusado. Se a versão mudar, use uma biblioteca separada ou atualize referências autorizadas; embeddings V1/V2 não se misturam. O arquivo S3 mencionado na documentação antiga retornou 404, por isso não é usado.

O wrapper corrige a inicialização de `ToneColorConverter`: o upstream encaminha `enable_watermark` a uma base que não aceita o argumento. A subclasse local inicializa a base diretamente, não carrega `wavmark` e usa `torch.load(weights_only=True)` após validar o checksum. Métodos do conversor e pesos permanecem originais. Arquivos finais são explicitamente identificados como sintéticos.

## Referência inválida ou qualidade baixa

Confirme autorização e grave uma pessoa só, sem música, reverberação ou falas sobrepostas. Grave 15–60 segundos, sem saturação, no mesmo microfone/distância. A biblioteca recusa ausência de fala ou embedding inválido. Consistência de locutores e ruído são heurísticos; ouça a referência e a prévia. Não prometa identificar todos os locutores automaticamente.

Voz diferente no resultado pode decorrer da voz base, sotaque, prosódia, referência inadequada ou limites do conversor. `tau` não é um botão de emoção. Pronúncia brasileira vem do Piper PT-BR; a conversão de timbre pode mudar a percepção de naturalidade. Ajuste texto e pontuação, compare velocidade e gere outra prévia.

## Arquivos e biblioteca

FFmpeg e FFprobe precisam estar no PATH ou ter caminhos configurados. Arquivos protegidos, inválidos ou sem faixa de áudio geram erro. TXT precisa ser UTF-8. Destino existente nunca é sobrescrito; use nome novo. Não edite `speaker.npy` ou metadados manualmente: checksums detectam alterações.

Se a skill não aparecer, reinicie o Codex e confira o diretório de skills. O runner pode ser executado de outro projeto. Se um lock estiver ocupado, aguarde o processo anterior; uma segunda operação pode exceder o timeout e deve ser repetida após o fim. Atualização de skill não deve apagar `data` nem modelos.

## Publicação e uso externo

Não envie referências, embeddings, ZIPs privados ou narrações sem autorização explícita. O repositório deve conter somente código, documentação e testes sintéticos. Se `gh` não estiver autenticado ou não puder criar repositórios, preserve o projeto local e reporte o erro sem expor tokens.

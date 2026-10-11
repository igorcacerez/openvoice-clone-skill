# Validação realizada em 11 de outubro de 2026

Ambiente: Windows 11 nativo, Python 3.11.16, NVIDIA GTX 1650 com 4 GB de VRAM, PyTorch 2.5.1+cu118, OpenVoice V2 e Piper 1.8.0 em ambientes separados.

| Verificação | Evidência |
|---|---|
| Dependências dos dois ambientes | `uv pip check`: todos os pacotes compatíveis |
| Modelo V2 | Checksum oficial validado e checkpoint carregado na GPU |
| TTS PT-BR | Piper Faber medium sintetizou referência e narrações reais |
| Embedding | Extração real `(1,256,1)` e recuperação sem pickle |
| Testes completos | `16 passed, 7 warnings in 149.75s` |
| Qualidade estática | `ruff check src scripts tests`: passou |
| Sintaxe | `compileall`: passou |
| WAV curto de integração | 6,12 segundos, mono, PCM, 44.1 kHz |
| MP3 longo de integração | 91,21 segundos, oito segmentos, 44.1 kHz |
| Inglês com o mesmo perfil | WAV de 3,15 segundos |
| CRUD e export/import | Cadastro, recuperação, renomeação, exclusão recuperável, importação/exportação testados |
| Integridade e entradas inválidas | Conflitos, checksums, ZIP inseguro, pickle e áudio inválido recusados |
| Consentimento | Cadastro/importação sem confirmação recusados antes da clonagem |
| Persistência entre processos/projetos | Runner da skill executado em outro projeto, recuperando o perfil da biblioteca global |
| Instalação da skill | `quick_validate.py`: `Skill is valid!` |
| Reinstalação preservando dados | Instalador finalizou e doctor encontrou o perfil existente |

O teste automatizado de inferência usa exclusivamente uma referência sintética, originada no Piper, e uma biblioteca isolada. Um perfil adicional foi cadastrado a partir de uma gravação com autorização explícita do usuário, e gerou uma prévia local de 11,44 segundos; dados desse perfil não fazem parte do repositório.

As verificações medem execução, persistência e integridade dos artefatos. Não demonstram semelhança perceptiva perfeita com uma pessoa, ausência garantida de múltiplos locutores, ausência de ruído ou naturalidade profissional. A avaliação auditiva do usuário continua necessária. Avisos de depreciação das dependências são conhecidos e não causaram falhas.

Não foram validadas inferência V1, francês opcional, Linux/WSL2 em hardware real nem recuperação depois de reiniciar o computador inteiro. Persistência foi validada após reiniciar processos e mudar de projeto, sem reinicializar o sistema operacional. Os seis idiomas nativos do pipeline MeloTTS não estão instalados nesta aplicação.

# Operações e persistência

Passe os argumentos a `scripts/run.py` ou à CLI instalada.

```text
voices rename "Nome antigo" "Nome novo"
voices update "Nome" --audio "referencia.wav" --consent-confirmed
voices delete "Nome"
voices export "Nome" --output "backup-da-voz.zip"
voices import "backup-da-voz.zip" --name "Nome" --consent-confirmed
history --limit 10
```

ZIP exportado contém dados vocais privados: referência, embedding e metadados. Não publique, envie a terceiros ou comite esses arquivos. Importação exige consentimento e cria novo ID. A implementação rejeita caminhos extras, links, checksums inválidos e embeddings pickle.

`data/voices/voice_UUID/rev_UUID/` contém `reference.wav`, `speaker.npy` e `metadata.json`. SQLite guarda os nomes, a revisão ativa e o histórico. Nomes são comparados sem diferenciar maiúsculas, após normalização Unicode. Atualizações preservam as revisões anteriores. Exclusões saem da listagem e vão para `data/trash`, junto com o registro anterior.

Para backup completo, feche processos de geração e copie o diretório `data` inteiro, incluindo SQLite e arquivos WAL/SHM se existirem. Para restore portable, importe os ZIPs individuais. Para restaurar backup completo, configure `OPENVOICE_DATA` para a cópia íntegra. Não misture o banco de um backup com arquivos de outra data.

Cada perfil registra a versão e o hash do conversor. V1/V2 não compartilham embeddings. Se alterar o checkpoint, recalcule o perfil com `voices update` a partir de uma referência autorizada. Só use checkpoints oficiais; a skill nunca carrega pickle fornecido pelo usuário.

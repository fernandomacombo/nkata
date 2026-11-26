# Avaliação de alojamento de media — etapa 68
Data: 25-11-2026. Avaliação, não contratação.

## Candidatos
| Fornecedor | Plano | Recursos | Tráfego anunciado | Mensal |
|---|---|---|---|---|
| LinuxVPS.co.za (Rackzar) | KLX1 | 1 vCPU, 2 GB, 25 GB NVMe | 250 GB | R99 (~387 MT) |
| LinuxVPS.co.za (Rackzar) | KLX2 | 2 vCPU, 4 GB, 60 GB NVMe | 500 GB | R199 (~778 MT) |
| Domains.co.za | EPYC VPS 1 | 1 vCPU, 2 GB, 50 GB NVMe | ilimitado anunciado, porta 500 Mbps | R209 (~817 MT) |
| Vultr Johannesburg | Cloud Compute | 1 vCPU, 2 GB, 55 GB | 2 TB anunciado por comparador | US$10 (~639 MT), confirmar no checkout |

Estimativas em MT a 3,91 MT/ZAR e 63,91 MT/USD; taxas bancárias, câmbio e
extras podem alterar o total. Preços e disponibilidade não garantidos.
Vultr: confirmar preço regional; não foi possível abrir a tabela oficial.
Fontes:
- https://www.linuxvps.co.za/
- https://www.domains.co.za/vps-hosting
- https://server.best/locations/johannesburg
- https://blogs.vultr.com/Vultr-announces-new-data-center-location-in-Johannesburg-South-Africa
- https://docs.vultr.com/support/platform/billing/what-is-the-bandwidth-overage-rate
- https://www.bancomoc.mz/pt/areas-de-actuacao/mercados/mercado-cambial/

## Estimativa de tráfego
Duas direcções, egress agregado SFU: 2 * bitrate por membro * duração.
Com 64 kbps de áudio: 57,6 MB/h; com vídeo+áudio 500 kbps: 450 MB/h;
com 1 Mbps: 900 MB/h. São valores teóricos, antes de overhead, retransmissões,
e contabilização do TURN. Se relay e SFU estiverem em hosts distintos, a
transferência entre ambos pode ser cobrada adicionalmente. Uma quota de
250 GB comportaria cerca de 278 horas de chamada a 1 Mbps por membro sem
overhead; reservar margem e medir antes de extrapolar. A capacidade de
chamadas simultâneas depende de CPU, rede, codecs e utilização real.

## Escolha preliminar
KLX1 como candidato económico para ensaio pequeno; KLX2 se for necessário
mais CPU/RAM. Vultr como alternativa com quota superior. Não usar produção
para o ensaio. Priorizar Johannesburg e medir RTT/jitter/perda desde redes
móveis de Moçambique e RTT HTTPS entre SFU e Django Railway (iad); sem
medição, proximidade geográfica não garante latência nem qualidade.
Confirmar IPv4 público, autorização de tráfego UDP/TCP, portas necessárias,
ACL/firewall, quotas e política de utilização; confirmar se SFU e TURN
podem partilhar o mesmo host com isolamento ou se exigem hosts separados.
Nenhuma compra autorizada/efectuada; CI e lockfiles da etapa 66 pendentes.

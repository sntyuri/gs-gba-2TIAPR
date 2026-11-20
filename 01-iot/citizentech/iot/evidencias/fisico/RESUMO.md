Teste realizado em 19/11/2026 com o ESP32 DevKit, o VL53L0X, o DHT22, o botão e os três LEDs, publicando no broker público HiveMQ, com o receptor gravando no banco SQLite. As figuras abaixo são quadros do vídeo de demonstração entregue junto com este relatório.

| Dado registrado no banco (dispositivo esp32-01) | Valor |
|---|---|
| Leituras periódicas | 206 (temperatura de 24,7 a 25,9 °C; umidade de 64,8% a 81,3%) |
| Buracos leves | 15 (profundidade de 15 a 37 mm) |
| Buracos graves | 17 (a partir de 42 mm) |
| Reportes manuais pelo botão | 15 |
| Calibrações | 2 |
| Resultado no ranking | trecho de teste (SIM0001) em prioridade alta, com alertas de buraco grave e de reporte emitidos pelo receptor |

**Situações executadas no hardware:** 1 (pista plana), 2 (buracos leve e grave) e 4 (botão de reporte). As situações 3 (umidade ≥ 85%) e 5 (comando de volta ao veículo) foram demonstradas com o simulador (seções 6.2 e 6.3): no ambiente de teste a umidade máxima foi 81,3%, abaixo do limiar de pista úmida.

Dois eventos graves registraram 469 e 532 mm porque o sensor foi levantado durante os testes. Em um veículo real, profundidades fora da faixa plausível devem ser descartadas (seção 7).
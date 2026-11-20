// Copie este arquivo para "credenciais.h" (mesma pasta) e preencha.
// credenciais.h está no .gitignore: a senha do Wi-Fi não vai para o repositório.
#pragma once

#define WIFI_SSID   "NOME_DA_REDE"     // o ESP32 só conecta em redes 2.4 GHz
#define WIFI_SENHA  "SENHA_DA_REDE"

// Opcionais (os valores padrão estão em src/main.cpp):
// #define MQTT_HOST      "broker.hivemq.com"
// #define MQTT_PORTA     1883
// #define TOPICO_BASE    "fiap/citizentech/gohorse-gs2026"   // igual ao MQTT_BASE do config.py
// #define DEVICE_ID      "esp32-01"
// #define TRECHO_INICIAL "SIM0001"

# RCSC Earthquake & Tsunami Statistic Home-Assistant Custom-Component

## Add to HACS

1. Setup `HACS` https://hacs.xyz/docs/setup/prerequisites
2. In `Home Assistant`, click `HACS` on the menu on the left
3. Select `integrations`
4. Click the menu button in the top right hand corner
5. Choose `custom repositories`
6. Enter `https://github.com/thematrixdev/home-assistant-rcsc-earthquake-tsunami` and choose `Integration`, click `ADD`
7. Find and click on `RCSC Earthquake & Tsunami` in the `custom repositories` list
8. Click the `DOWNLOAD` button in the bottom right hand corner
9. Restart Home Assistant

## Install

1. Go to `Settings`, `Devices and Services`
2. Click the `Add Integration` button
3. Search `RCSC Earthquake & Tsunami`
4. Go through the configuration flow

### Configuration Parameters

During setup, you'll need to configure the following parameters:

1. **Notification Criteria** (Required - Choose one):
   - **JMA Scale**: Set a minimum JMA seismic intensity scale (e.g., "3", "4", "5-", "5+", "6-", "6+", "7")
   - **Magnitude**: Set a minimum earthquake magnitude (e.g., 4.0, 5.0, 6.0)

2. **Notify Radius** (Optional):
   - Set the maximum distance (in kilometers) from your Home Assistant location to receive notifications about earthquakes
   - If not set, you will receive notifications for all earthquakes in Japan that meet your scale/magnitude criteria

3. **Consent** (Required):
   - You must acknowledge that this is not an Earthquake Early Warning system and there will be delays in notifications

## Sensors

The integration provides two binary sensors:

1. **RCSC Earthquake**: Shows `ON` when:
   - An earthquake meets your configured criteria (scale or magnitude)
   - Is within your specified notify radius (if radius is set)
   - Occurred within the last 30 minutes

2. **RCSC Tsunami**: Shows `ON` when:
   - There are active tsunami advisories
   - Additional information about affected locations is available in the sensor attributes

## Debug

### Basic

- On Home Assistant, go to `Settings` -> `Logs`
- Search `RCSC Earthquake & Tsunami`

### Advanced

- Add these lines to `configuration.yaml`

```yaml
logger:
  default: info
  logs:
    custom_components.rcsc_earthquake_tsunami: debug
```

- Restart Home Assistant
- On Home Assistant, go to `Settings` -> `Logs`
- Search `RCSC Earthquake & Tsunami`
- Click the `LOAD FULL LOGS` button

## Support

- Open an issue on GitHub
- Specify:
    - What's wrong
    - Home Assistant version
    - Integration version
    - Debug logs if applicable

## Unofficial support

- Telegram Group https://t.me/smarthomehk

## Tested on

- Ubuntu 24.10
- Home Assistant Container 2025.01

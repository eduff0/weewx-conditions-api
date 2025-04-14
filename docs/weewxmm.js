/* MagicMirrorÂ²
 * Module: Weather
 * Provider: weewxmm
 *
 * Provider Name: WeeWX_MagicMirror
 * Description: Retrieves current weather data from a WeeWX REST API.
 *
 * This provider complies with the WeatherProvider interface:
 * - init(config): Initializes the provider.
 * - setConfig(config): Sets the configuration (and checks for required values).
 * - fetchCurrentWeather(): Fetches current weather data.
 * - fetchWeatherForecast(): Returns an empty forecast array.
 * - fetchWeatherHourly(): Returns an empty hourly array.
 * - parseCurrentWeather(data): Converts API data into a WeatherObject.
 *
 * See: https://docs.magicmirror.builders/development/weather-provider.html
 */

WeatherProvider.register("weewxmm", {
  providerName: "WeeWX_MagicMirror",

  init: function(config) {
    // Simply store the initial configuration
    this.config = config || {};
    Log.log(`${this.providerName} initialized.`);
  },

  /**
   * Sets the provider configuration.
   * Checks for the required "apiBase" configuration value.
   * @param {object} config - The configuration object.
   */
  setConfig: function(config) {
    this.config = config;
    if (!this.config.apiBase) {
      Log.error(`${this.providerName}: Missing required configuration value 'apiBase'.`);
    }
  },

  fetchCurrentWeather: function() {
    var self = this;
    // Get the base URL from the config (strip any trailing slash)
    var baseURL = this.config.apiBase.replace(/\/$/, "");
    var url = baseURL + "/api/mmwo";

    // Ping the base URL to check reachability, then proceed.
    fetch(baseURL, { method: "HEAD", mode: "no-cors" })
      .then(function() {
        self._doFetchCurrentWeather(url);
      })
      .catch(function() {
        self._doFetchCurrentWeather(url);
      });
  },

  _doFetchCurrentWeather: function(url) {
    var self = this;
    this.fetchData(url)
      .then(function(data) {
        var currentWeather = self.parseCurrentWeather(data);
        self.setCurrentWeather(currentWeather);
        self.updateAvailable();
      })
      .catch(function(error) {
        Log.error(`${self.providerName} fetchCurrentWeather() failed: ${error}`);
      });
  },

  fetchWeatherForecast: function() {
    this.setWeatherForecast([]);
    this.updateAvailable();
  },

  fetchWeatherHourly: function() {
    this.setWeatherHourly([]);
    this.updateAvailable();
  },

  parseCurrentWeather: function(data) {
    var current = new WeatherObject();
    current.date = moment(data.timestamp);
    current.sunrise = moment(data.sunrise);
    current.sunset = moment(data.sunset);
    current.temperature = data.temperature;
    current.windSpeed = data.windSpeed;
    current.windDirection = data.windDirection;
    current.humidity = data.humidity;
    current.pressure = data.pressure;
    return current;
  }
});

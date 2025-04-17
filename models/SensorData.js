const mongoose = require('mongoose');

const SensorDataSchema = new mongoose.Schema({
  deviceId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Device',
    required: true
  },
  type: {
    type: String,
    enum: ['food', 'water', 'temperature', 'humidity'],
    required: true
  },
  value: {
    type: Number,
    required: true
  },
  timestamp: {
    type: Date,
    default: Date.now
  }
});

// Index to optimize queries by deviceId, type and timestamp
SensorDataSchema.index({ deviceId: 1, type: 1, timestamp: -1 });

module.exports = mongoose.model('SensorData', SensorDataSchema);
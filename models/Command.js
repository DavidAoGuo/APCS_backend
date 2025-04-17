const mongoose = require('mongoose');

const CommandSchema = new mongoose.Schema({
  deviceId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Device',
    required: true
  },
  type: {
    type: String,
    enum: ['dispenseFood', 'dispenseWater', 'setTemperature'],
    required: true
  },
  value: {
    type: Number,
    required: true
  },
  status: {
    type: String,
    enum: ['pending', 'processing', 'completed', 'failed'],
    default: 'pending'
  },
  timestamp: {
    type: Date,
    default: Date.now
  }
});

// Index to optimize queries
CommandSchema.index({ deviceId: 1, status: 1, timestamp: -1 });

module.exports = mongoose.model('Command', CommandSchema);
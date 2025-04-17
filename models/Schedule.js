const mongoose = require('mongoose');

const ScheduleSchema = new mongoose.Schema({
  deviceId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Device',
    required: true
  },
  type: {
    type: String,
    enum: ['food', 'water'],
    required: true
  },
  time: {
    type: String, // HH:MM format
    required: true
  },
  days: {
    type: [String],
    enum: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    default: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  },
  amount: {
    type: Number,
    required: true,
    min: 1,
    max: 100
  },
  enabled: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Schedule', ScheduleSchema);
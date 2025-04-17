const express = require('express');
const router = express.Router();
const { 
  dispenseFood, 
  dispenseWater,
  setTemperature,
  testMqtt
} = require('../controllers/controlController');
const { protect } = require('../middleware/authMiddleware');

// All routes are protected
router.use(protect);

router.post('/dispense-food', dispenseFood);
router.post('/dispense-water', dispenseWater);
router.post('/set-temperature', setTemperature);
router.get('/test-mqtt', testMqtt);

module.exports = router;
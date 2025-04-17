const jwt = require('jsonwebtoken');
const User = require('../models/User');
const { verifyToken } = require('../utils/jwt');

const protect = async (req, res, next) => {
  let token;
  
  // Check if token exists in headers
  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    try {
      // Extract token from headers
      token = req.headers.authorization.split(' ')[1];
      
      // Verify token
      const decoded = verifyToken(token);
      
      if (!decoded) {
        return res.status(401).json({
          success: false,
          message: 'Not authorized, token failed'
        });
      }
      
      // Find user by ID (without password)
      req.user = await User.findById(decoded.id);
      
      if (!req.user) {
        return res.status(401).json({
          success: false,
          message: 'User not found'
        });
      }
      
      next();
    } catch (error) {
      console.error(error);
      return res.status(401).json({
        success: false,
        message: 'Not authorized, token failed'
      });
    }
  }
  
  if (!token) {
    return res.status(401).json({
      success: false,
      message: 'Not authorized, no token'
    });
  }
};

module.exports = { protect };
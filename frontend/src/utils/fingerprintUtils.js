// src/utils/fingerprintUtils.js

/**
 * Generate a browser fingerprint using available browser components
 * This is a simplified version for demonstration. For production,
 * consider using FingerprintJS or a similar library
 * @returns {Promise<string>} - A hash representing the browser fingerprint
 */
export async function generateBrowserFingerprint() {
  try {
    // Collect various browser characteristics
    const components = [
      // Screen and window info
      window.screen.colorDepth,
      window.screen.width,
      window.screen.height,
      window.screen.availWidth,
      window.screen.availHeight,

      // Browser capabilities
      navigator.language,
      navigator.languages,
      !!navigator.cookieEnabled,
      !!navigator.deviceMemory,
      navigator.hardwareConcurrency,

      // User agent (note: will be limited in some modern browsers)
      navigator.userAgent,

      // Time zone
      Intl.DateTimeFormat().resolvedOptions().timeZone,

      // Canvas fingerprinting - simplified version
      await getCanvasFingerprint(),

      // Audio context fingerprinting - simplified
      await getAudioFingerprint(),

      // WebGL capabilities
      await getWebGLInfo(),

      // Installed fonts (limited detection)
      await detectCommonFonts()
    ];

    // Create a string from all components
    const componentsString = components
      .flat()
      .filter(item => item !== undefined && item !== null)
      .join('|');

    // Use a simple hash function
    return await hashString(componentsString);

  } catch (error) {
    console.error('Error generating fingerprint:', error);
    // Fallback to a more basic fingerprint
    return hashString(navigator.userAgent + navigator.language + screen.width);
  }
}

/**
 * Creates a canvas fingerprint
 * @returns {Promise<string>} - Hash of canvas data
 */
async function getCanvasFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    // Set canvas dimensions
    canvas.width = 200;
    canvas.height = 50;

    // Draw text with specific styling
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#F60';
    ctx.fillRect(0, 0, 100, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('Browser Fingerprinting', 4, 2);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('Browser Fingerprinting', 2, 18);

    // Extract data URL
    return canvas.toDataURL();
  } catch (error) {
    return 'canvas-not-supported';
  }
}

/**
 * Creates an audio context fingerprint
 * @returns {Promise<string>} - Identifier based on audio processing
 */
async function getAudioFingerprint() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return 'audio-not-supported';

    const audioContext = new AudioContext();
    const oscillator = audioContext.createOscillator();
    const analyser = audioContext.createAnalyser();
    const gain = audioContext.createGain();

    // Connect the nodes
    oscillator.type = 'triangle';
    oscillator.connect(analyser);
    analyser.connect(gain);

    // Short analysis
    const values = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(values);

    // Clean up
    audioContext.close();

    return Array.from(values).slice(0, 5).join(',');
  } catch (error) {
    return 'audio-error';
  }
}

/**
 * Gets WebGL information for fingerprinting
 * @returns {Promise<string[]>} - WebGL capabilities
 */
async function getWebGLInfo() {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

    if (!gl) return ['webgl-not-supported'];

    return [
      gl.getParameter(gl.VENDOR),
      gl.getParameter(gl.RENDERER),
      gl.getParameter(gl.VERSION)
    ];
  } catch (error) {
    return ['webgl-error'];
  }
}

/**
 * Detects availability of common fonts
 * @returns {Promise<string[]>} - List of detected fonts
 */
async function detectCommonFonts() {
  const fontTestSize = '72px';
  const baseFonts = ['monospace', 'sans-serif', 'serif'];
  const fontList = [
    'Arial', 'Courier New', 'Georgia', 'Times New Roman',
    'Verdana', 'Helvetica', 'Comic Sans MS'
  ];

  const testString = 'mmmmmmmmmmlli';
  const testDiv = document.createElement('div');
  document.body.appendChild(testDiv);

  const baseFontWidths = {};
  const detectedFonts = []; // Changed variable name to avoid conflict

  // Check width with base fonts
  for (const baseFont of baseFonts) {
    testDiv.style.fontFamily = baseFont;
    testDiv.style.fontSize = fontTestSize;
    testDiv.innerHTML = testString;
    baseFontWidths[baseFont] = testDiv.offsetWidth;
  }

  // Test each font
  for (const font of fontList) {
    let isDetected = false; // Changed variable name to avoid conflict

    for (const baseFont of baseFonts) {
      testDiv.style.fontFamily = `${font}, ${baseFont}`;
      if (testDiv.offsetWidth !== baseFontWidths[baseFont]) {
        isDetected = true;
        break;
      }
    }

    if (isDetected) {
      detectedFonts.push(font); // Now detectedFonts is an array, so push() works
    }
  }

  // Clean up
  document.body.removeChild(testDiv);

  return detectedFonts;
}

/**
 * Simple hash function for strings
 * @param {string} str - String to hash
 * @returns {Promise<string>} - Hashed string
 */
async function hashString(str) {
  if (!str) return 'empty-input';

  // Use SubtleCrypto if available (more secure)
  if (window.crypto && window.crypto.subtle && window.TextEncoder) {
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(str);
      const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (e) {
      // Fall back to simple hash
    }
  }

  // Simple hash function fallback
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString(36);
}

/**
 * Get or create a device fingerprint and store in localStorage
 * @returns {Promise<string>} - The fingerprint
 */
export async function getDeviceFingerprint() {
  // Try to get stored fingerprint first
  const storedFingerprint = localStorage.getItem('device_fingerprint');

  if (storedFingerprint) {
    return storedFingerprint;
  }

  // Generate new fingerprint
  const fingerprint = await generateBrowserFingerprint();

  // Store for future use
  localStorage.setItem('device_fingerprint', fingerprint);

  return fingerprint;
}
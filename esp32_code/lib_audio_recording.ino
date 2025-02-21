#include "driver/i2s_std.h"     // Include I2S standard driver for ESP32

// --- defines & macros --------

#ifndef DEBUG                  
#  define DEBUG true            // Enable debug mode
#  define DebugPrint(x);        if(DEBUG){Serial.print(x);}    // Debug print macro
#  define DebugPrintln(x);      if(DEBUG){Serial.println(x);}  // Debug println macro
#endif


// --- PIN assignments ---------
// I2S pins configuration for the INMP441 microphone
#define I2S_WS      27          // Word Select (L/R clock) pin 
#define I2S_SD      33          // Serial Data pin for audio input
#define I2S_SCK     32          // Serial Clock pin for I2S timing

//L/R pin INMP441 on Vcc is RIGHT channel, connected to GND is LEFT channel (Set to LEFT on the cactus project)



// --- define your settings ----
#define SAMPLE_RATE             16000  // Audio sampling rate in Hz
#define BITS_PER_SAMPLE         8      // Bits per sample (8 or 16 bit audio)
#define GAIN_BOOSTER_I2S        10     // Amplification factor for microphone input

// --- global vars -------------
// Standard I2S configuration structure
i2s_std_config_t  std_cfg = 
{ .clk_cfg  =   
  { .sample_rate_hz = SAMPLE_RATE,          // Set sampling rate
    .clk_src = I2S_CLK_SRC_DEFAULT,         // Set sampling rate
    .mclk_multiple = I2S_MCLK_MULTIPLE_256, // Set sampling rate
  },
  .slot_cfg =   
  { 
    .data_bit_width = I2S_DATA_BIT_WIDTH_16BIT,   // Data width for each sample
    .slot_bit_width = I2S_SLOT_BIT_WIDTH_AUTO,    // Automatic slot width
    .slot_mode = I2S_SLOT_MODE_MONO,              // Mono audio mode
    .slot_mask = I2S_STD_SLOT_LEFT,               // Use left channel
    .ws_width =  I2S_DATA_BIT_WIDTH_16BIT,        // Word select width    
    .ws_pol = false,                              // Word select polarity
    .bit_shift = true,                            // Enable bit shifting
    .msb_right = false,                           // MSB position
  },
  .gpio_cfg =   
  { .mclk = I2S_GPIO_UNUSED,       // Master clock pin (unused)
    .bclk = (gpio_num_t) I2S_SCK,  // Bit clock pin
    .ws   = (gpio_num_t) I2S_WS,   // Word select pin
    .dout = I2S_GPIO_UNUSED,       // Data out pin (unused)
    .din  = (gpio_num_t) I2S_SD,   // Data in pin
    .invert_flags =                // Clock inversion flags
    { .mclk_inv = false,
      .bclk_inv = false,
      .ws_inv = false,
    },
  },
};

// [re_handle]: global handle to the RX channel with channel configuration [std_cfg]
i2s_chan_handle_t  rx_handle;


// [myWAV_Header]: selfmade WAV Header:
struct WAV_HEADER 
{ char  riff[4] = {'R','I','F','F'};                       // RIFF header
  long  flength = 0;                                       // Total file length in bytes (calculated at end)
  char  wave[4] = {'W','A','V','E'};                       // WAVE header
  char  fmt[4]  = {'f','m','t',' '};                       // Format chunk marker
  long  chunk_size = 16;                                   // Format chunk size in bytes (usually 16)
  short format_tag = 1;                                    // Audio format (1=PCM, 257=Mu-Law, 258=A-Law, 259=ADPCM)
  short num_chans = 1;                                     // Number of channels (1=mono, 2=stereo)
  long  srate = SAMPLE_RATE;                               // Sample rate per second
  long  bytes_per_sec = SAMPLE_RATE * (BITS_PER_SAMPLE/8); // Bytes per second srate * bytes_per_samp
  short bytes_per_samp = (BITS_PER_SAMPLE/8);              // Bytes per sample (2=16-bit mono, 4=16-bit stereo)
  short bits_per_samp = BITS_PER_SAMPLE;                   // Bytes per sample
  char  dat[4] = {'d','a','t','a'};                        // "data" 
  long  dlength = 0;                                       // Data length (calculated at end) in bytes (calculated at end)
} myWAV_Header;


bool flg_is_recording = false;      

bool flg_I2S_initialized = false;      


// ------------------------------------------------ Function: I2S_Record_Init ------------------------------------------------

// Initializes I2S interface for recording
bool I2S_Record_Init() 
{  
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
  
  i2s_new_channel(&chan_cfg, NULL, &rx_handle);     // Allocate a new RX channel and get the handle of this channel
  i2s_channel_init_std_mode(rx_handle, &std_cfg);   // Initialize the channel
  i2s_channel_enable(rx_handle);                    // Before reading data, start the RX channel first
  
  flg_I2S_initialized = true;                      

  return flg_I2S_initialized;  
}



// ------------------------------------------------ Function: Record_Start ------------------------------------------------
// Handles recording process: initializes file and writes audio data
bool Record_Start( String audio_filename ) 
{ 
  if (!flg_I2S_initialized)     
  {  Serial.println( "ERROR in Record_Start() - I2S not initialized, call 'I2S_Record_Init()' missed" );    
     return false;
  }

  if (!flg_is_recording)  // entering 1st time -> remove old AUDIO file, create new file with WAV header
  { 
    flg_is_recording = true;
    // Create new file with WAV header
    if (SD.exists(audio_filename)) 
    {  SD.remove(audio_filename); DebugPrintln("\n> Existing AUDIO file removed.");
    }  else {DebugPrintln("\n> No AUDIO file found");}
    
    File audio_file = SD.open(audio_filename, FILE_WRITE);
    audio_file.write((uint8_t *) &myWAV_Header, 44);
    audio_file.close(); 
    
    DebugPrintln("> WAV Header generated, Audio Recording started ... ");
    return true;
  }
  
  // Continuous recording process
  if (flg_is_recording)  
  { 
    // Array to store Original audio I2S input stream (reading in chunks, e.g. 1024 values) 
    int16_t audio_buffer[1500];         // Buffer for 16-bit samples
    uint8_t audio_buffer_8bit[1500];    // Buffer for 8-bit samples

    // Read from I2S input stream (with <I2S_std.h>)
    size_t bytes_read = 0;
    i2s_channel_read(rx_handle, audio_buffer, sizeof(audio_buffer), &bytes_read, portMAX_DELAY);

    // Apply gain boost if configured
    if ( GAIN_BOOSTER_I2S > 1 && GAIN_BOOSTER_I2S <= 64 );    
    for (int16_t i = 0; i < ( bytes_read / 2 ); ++i)         
    {   audio_buffer[i] = audio_buffer[i] * GAIN_BOOSTER_I2S;  
    }

    // Apply gain boost if configured
    if (BITS_PER_SAMPLE == 8)
    { for (int16_t i = 0; i < ( bytes_read / 2 ); ++i)        
      { audio_buffer_8bit[i] = (uint8_t) ((( audio_buffer[i] + 32768 ) >>8 ) & 0xFF); 
      }
    }

    // Write to file
    File audio_file = SD.open(audio_filename, FILE_APPEND);
    if (audio_file)
    {  
       if (BITS_PER_SAMPLE == 16) // 16 bit default
       {  audio_file.write((uint8_t*)audio_buffer, bytes_read);
       }        
       if (BITS_PER_SAMPLE == 8)  // 8bit mode
       {  audio_file.write((uint8_t*)audio_buffer_8bit, bytes_read/2);
       }  
       audio_file.close(); 
       return true; 
    }  
    
    if (!audio_file) 
    { Serial.println("ERROR in Record_Start() - Failed to open audio file!"); 
      return false;
    }    
  }  
}


//------------------------------------------------ Function: Record_Available ------------------------------------------------
// Finalizes recording and updates WAV header with final file size
bool Record_Available( String audio_filename, float* audiolength_sec ) 
{

  if (!flg_is_recording) 
  {   return false;   
  }
  
  if (!flg_I2S_initialized)  
  {  return false;
  }
  
  // Update WAV header with final file size
  if (flg_is_recording) 
  { 
    
    File audio_file = SD.open(audio_filename, "r+");
    long filesize = audio_file.size();
    audio_file.seek(0); myWAV_Header.flength = filesize;  myWAV_Header.dlength = (filesize-8);
    audio_file.write((uint8_t *) &myWAV_Header, 44);
    audio_file.close(); 
    
    flg_is_recording = false; 
    
    // Calculate audio length in seconds
    *audiolength_sec = (float) (filesize-44) / (SAMPLE_RATE * BITS_PER_SAMPLE/8);   
     
    DebugPrintln("> ... Done. Audio Recording finished.");
    DebugPrint("> New AUDIO file: '" + audio_filename + "', filesize [bytes]: " + (String) filesize);
    DebugPrintln(", length [sec]: " + (String) *audiolength_sec);
    
    return true;   
  }  
}

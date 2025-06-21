// Function to get OpenGraph image from Spotify link
export const getSpotifyPreviewImage = async (spotifyUrl: string): Promise<string | null> => {
    try {
      const response = await fetch(`https://api.microlink.io?url=${encodeURIComponent(spotifyUrl)}&screenshot=false&video=false`);
      const data = await response.json();
  
      if (data.status === 'success' && data.data && data.data.image) {
        return data.data.image.url;
      }
      return null;
    } catch (error) {
      console.error('Error fetching preview image:', error);
      return null;
    }
  };
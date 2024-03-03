// Constructing base error
class AppError extends Error {
  constructor(message) {
    super(message);
    this.name = this.constructor.name;
  }
}

// Inheriting AppError attributes for Custom Errors
class NetworkError extends AppError {}
class DataFetchError extends AppError {}
class MapInitializationError extends AppError {}
class FetchAccidentsError extends AppError {}
class MarkerError extends AppError {}
class FormatError extends AppError {}

// Define a mapping from error constructors to error messages
const errorMessageMapping = {
  [NetworkError.name]: "Network issue, please try again later.",
  [DataFetchError.name]: "Problem fetching data.",
  [MapInitializationError.name]: "Failed to initialize the map.",
  [FetchAccidentsError.name]: "Could not load accident data.",
  [MarkerError.name]: "Error displaying map markers",
  [FormatError.name]: "Fetched data is not in expected format",
};

function handleError(error) {
  // Use the name of the error's constructor to get a specific message or use a generic message
  const message =
    errorMessageMapping[error.name] || "An unexpected error occurred.";
  displayUserErrorMessage(message);
}

function displayUserErrorMessage(message) {
  let errorContainer = document.getElementById("error-message-container");

  // If the error container does not exist, create it and append it to the body
  if (!errorContainer) {
    errorContainer = document.createElement("div");
    errorContainer.id = "error-message-container";
    document.body.appendChild(errorContainer);
    errorContainer.style =
      "position: fixed; top: 0; left: 0; width: 100%; background: rgba(255, 0, 0, 0.7); color: white; text-align: center; padding: 10px; box-sizing: border-box; z-index: 1000;";
  }

  errorContainer.setAttribute("role", "alert");

  // Set the error message
  errorContainer.innerHTML = `<div class="error-message" style="padding: 10px; margin: 10px 0; border-radius: 5px; background: #ffd1d1; color: red;">${message}</div>`;

  // Make the container visible
  errorContainer.style.display = "block";
}

document.addEventListener("DOMContentLoaded", async function () {
  try {
    await fetchAWSCredentialsAndInitializeMap(); // Fetch AWS credentials and initialize map
  } catch (error) {
    handleError(error); // Handle errors from both processes
  }
});

// Fetches AWS credentials and initializes the map
async function fetchAWSCredentialsAndInitializeMap() {
  try {
    const credentialsResponse = await fetch(
      "https://avalanchebackend.onrender.com/api/aws-credentials/"
    );
    if (!credentialsResponse.ok) {
      throw new Error(
        `Failed to fetch AWS credentials: status ${credentialsResponse.status}`
      );
    }
    const { identityPoolId, region, mapName } =
      await credentialsResponse.json();
    initializeMap(identityPoolId, region, mapName);
  } catch (error) {
    // Handle fetch-specific errors or other unexpected errors
    if (error.message.includes("Failed to fetch")) {
      handleError(new DataFetchError(error.message));
    } else {
      handleError(
        new DataFetchError(
          "An unexpected error occurred while fetching AWS credentials."
        )
      );
    }
  }
}

let map;

// Initializes the map and adds markers for each accident
async function initializeMap(identityPoolId, region, mapName) {
  try {
    const authHelper = await amazonLocationAuthHelper.withIdentityPoolId(
      identityPoolId
    );

    let zoomLevel = 4;
    if (window.innerWidth < 768) {
      zoomLevel -= 2;
    }

    // Initialize the global 'map' object
    map = new maplibregl.Map({
      container: "map",
      style: `https://maps.geo.${region}.amazonaws.com/maps/v0/maps/${mapName}/style-descriptor`,
      center: [-98.5795, 39.8283],
      zoom: zoomLevel,
      ...authHelper.getMapAuthenticationOptions(),
    });

    map.addControl(new maplibregl.NavigationControl(), "top-left");

    // Load event for when the map is ready to add markers
    map.on("load", async () => {
      await fetchAccidentsData(); // Fetch accident data after map is loaded
    });
  } catch (error) {
    handleError(new MapInitializationError());
  }
}

// Helper function to calculate the next update timestamp
function calculateNextUpdateTimestamp() {
  const now = new Date();
  const firstOfTheMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const fifteenthOfTheMonth = new Date(now.getFullYear(), now.getMonth(), 15);
  const firstOfNextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);

  if (now < firstOfTheMonth) {
    return firstOfTheMonth.getTime();
  } else if (now >= firstOfTheMonth && now < fifteenthOfTheMonth) {
    return fifteenthOfTheMonth.getTime();
  } else {
    return firstOfNextMonth.getTime();
  }
}

// Fetch data with caching logic
async function fetchAccidentsData() {
  const cachedData = localStorage.getItem("accidentsData");
  let accidents;

  if (cachedData) {
    const { data, expiry } = JSON.parse(cachedData);

    if (expiry > Date.now()) {
      // Use cached data if it's not expired
      accidents = data;
    }
  }

  // If there's no valid cached data, fetch new data
  if (!accidents) {
    try {
      const response = await fetch(
        "https://avalanchebackend.onrender.com/api/accidents/"
      );
      if (!response.ok) {
        handleError(new FetchAccidentsError());
        return;
      }
      accidents = await response.json();

      // Cache the new data with an expiry timestamp
      localStorage.setItem(
        "accidentsData",
        JSON.stringify({
          data: accidents,
          expiry: calculateNextUpdateTimestamp(),
        })
      );
    } catch (error) {
      handleError(error);
      return; // Exit the function if an error occurs
    }
  }

  if (!Array.isArray(accidents)) {
    handleError(new FormatError("Fetched data is not in expected format."));
    return;
  }

  // Add accidents data to the map
  addAccidentsToMap(accidents);
}

// Adds markers to the map for each accident, ensuring valid latitude and longitude
function addAccidentsToMap(accidents) {
  // Check if the map object is defined
  if (!map) {
    handleError(new MarkerError());
    return; // Exit the function if the map is not defined
  }

  accidents.forEach((accident) => {
    // Ensure latitude and longitude are defined and are numbers
    if (
      typeof accident.latitude !== "number" ||
      typeof accident.longitude !== "number"
    ) {
      return; // Skip this iteration if latitude or longitude data is invalid
    }

    try {
      // Proceed to create and add the marker with a popup
      new maplibregl.Marker()
        .setLngLat([accident.longitude, accident.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(
            `<h3>${accident.location}, ${accident.state}</h3><p>${accident.description}</p><p>Date: ${accident.date}</p>`
          )
        )
        .addTo(map);
    } catch (error) {
      handleError(new MarkerError());
    }
  });
}

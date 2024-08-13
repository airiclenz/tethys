
# URL of the web service
URL="http://localhost:5000/api/initializeDatabase/"

# Call the web service and save the response in a variable
RESPONSE=$(curl -s $URL)

# Print the response
echo "Raw Response:      " $RESPONSE

# Format the JSON response using jq
FORMATTED_RESPONSE=$(echo $RESPONSE | jq '.')

# Print the response
echo "Formatted Response:" $FORMATTED_RESPONSE
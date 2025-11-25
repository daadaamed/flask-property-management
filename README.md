# flask-property-management

## API REST to manage properties having these features :
- Handle Users
- Update a user ( only user himself)
- Handle properties
- Filter by cities
- Modify a property only by its owner

## Install and run
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate sur Windows
pip install -r requirements.txt
flask init-db
flask --app app run --debug
```


DB configuration:
```bash
docker compose up -d db              
```

## API tests
#### Create user
```bash
curl -X POST http://127.0.0.1:5000/users \
  -H "Content-Type: application/json" \
  -d '{
        "first_name": "Alice",
        "last_name": "Owner",
        "date_of_birth": "1990-01-01"
      }'
```

#### Get a user

```bash
curl -X GET http://localhost:5000/users/1
```

#### Create a property
```bash
curl -X POST http://127.0.0.1:5000/properties \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
        "name": "Appartement centre-ville",
        "description": "Super appart proche métro",
        "property_type": "apartment",
        "city": "Paris",
        "rooms_details": [
          {"name": "chambre", "size": 12},
          {"name": "salon", "size": 20}
        ]
      }'
```

#### Update a property
```bash
curl -X PATCH http://127.0.0.1:5000/properties/1 \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
        "name": "Appartement rénové",
        "rooms_details": [
          {"name": "chambre", "size": 13},
          {"name": "salon", "size": 22},
          {"name": "bureau", "size": 9}
        ]
      }'
```

#### Get properties
```bash
curl http://127.0.0.1:5000/properties
```

#### Get properties by city
```bash
curl "http://127.0.0.1:5000/properties?city=paris"
```

#### Delete a property
```bash
curl -X DELETE http://127.0.0.1:5000/properties/1 \
  -H "X-User-Id: 1"
```
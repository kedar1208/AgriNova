"""States and districts the app knows about.

Districts are a fixed pick-list (not free text) so a typo or random text can never be shown as a real place.
Coordinates are looked up from the district name at run time (Open-Meteo geocoder); if that fails the state's
reference point is used and the UI says so. Names follow current official usage; SEARCH_ALIASES lists older
spellings the geocoder may know better."""

DISTRICTS = {
    "Andhra Pradesh": ["Alluri Sitharama Raju", "Anakapalli", "Anantapur", "Annamayya", "Bapatla", "Chittoor", "East Godavari",
                       "Eluru", "Guntur", "Kakinada", "Konaseema", "Krishna", "Kurnool", "Nandyal", "NTR (Vijayawada)", "Palnadu",
                       "Parvathipuram Manyam", "Prakasam", "Nellore", "Sri Sathya Sai", "Srikakulam", "Tirupati", "Visakhapatnam",
                       "Vizianagaram", "West Godavari", "YSR Kadapa"],
    "Bihar": ["Araria", "Arwal", "Aurangabad", "Banka", "Begusarai", "Bhagalpur", "Bhojpur", "Buxar", "Darbhanga", "East Champaran",
              "Gaya", "Gopalganj", "Jamui", "Jehanabad", "Kaimur", "Katihar", "Khagaria", "Kishanganj", "Lakhisarai", "Madhepura",
              "Madhubani", "Munger", "Muzaffarpur", "Nalanda", "Nawada", "Patna", "Purnia", "Rohtas", "Saharsa", "Samastipur",
              "Saran", "Sheikhpura", "Sheohar", "Sitamarhi", "Siwan", "Supaul", "Vaishali", "West Champaran"],
    "Chhattisgarh": ["Balod", "Baloda Bazar", "Balrampur", "Bastar", "Bemetara", "Bijapur", "Bilaspur", "Dantewada", "Dhamtari", "Durg",
                     "Gariaband", "Janjgir-Champa", "Jashpur", "Kabirdham", "Kanker", "Khairagarh", "Kondagaon", "Korba", "Koriya",
                     "Mahasamund", "Manendragarh", "Mohla-Manpur", "Mungeli", "Narayanpur", "Raigarh", "Raipur", "Rajnandgaon",
                     "Sakti", "Sarangarh-Bilaigarh", "Sukma", "Surajpur", "Surguja"],
    "Gujarat": ["Ahmedabad", "Amreli", "Anand", "Aravalli", "Banaskantha", "Bharuch", "Bhavnagar", "Botad", "Chhota Udaipur", "Dahod",
                "Dang", "Devbhoomi Dwarka", "Gandhinagar", "Gir Somnath", "Jamnagar", "Junagadh", "Kheda", "Kutch", "Mahisagar",
                "Mehsana", "Morbi", "Narmada", "Navsari", "Panchmahal", "Patan", "Porbandar", "Rajkot", "Sabarkantha", "Surat",
                "Surendranagar", "Tapi", "Vadodara", "Valsad"],
    "Haryana": ["Ambala", "Bhiwani", "Charkhi Dadri", "Faridabad", "Fatehabad", "Gurugram", "Hisar", "Jhajjar", "Jind", "Kaithal",
                "Karnal", "Kurukshetra", "Mahendragarh", "Nuh", "Palwal", "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa",
                "Sonipat", "Yamunanagar"],
    "Karnataka": ["Bagalkot", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban", "Bidar", "Chamarajanagar", "Chikkaballapur",
                  "Chikkamagaluru", "Chitradurga", "Dakshina Kannada", "Davanagere", "Dharwad", "Gadag", "Hassan", "Haveri",
                  "Kalaburagi", "Kodagu", "Kolar", "Koppal", "Mandya", "Mysuru", "Raichur", "Ramanagara", "Shivamogga", "Tumakuru",
                  "Udupi", "Uttara Kannada", "Vijayanagara", "Vijayapura", "Yadgir"],
    "Madhya Pradesh": ["Agar Malwa", "Alirajpur", "Anuppur", "Ashoknagar", "Balaghat", "Barwani", "Betul", "Bhind", "Bhopal",
                       "Burhanpur", "Chhatarpur", "Chhindwara", "Damoh", "Datia", "Dewas", "Dhar", "Dindori", "Guna", "Gwalior",
                       "Harda", "Indore", "Jabalpur", "Jhabua", "Katni", "Khandwa", "Khargone", "Maihar", "Mandla", "Mandsaur",
                       "Mauganj", "Morena", "Narsinghpur", "Neemuch", "Niwari", "Pandhurna", "Panna", "Raisen", "Rajgarh", "Ratlam",
                       "Rewa", "Sagar", "Satna", "Sehore", "Seoni", "Shahdol", "Shajapur", "Sheopur", "Shivpuri", "Sidhi",
                       "Singrauli", "Tikamgarh", "Ujjain", "Umaria", "Vidisha"],
    "Maharashtra": ["Ahilyanagar", "Akola", "Amravati", "Beed", "Bhandara", "Buldhana", "Chandrapur", "Chhatrapati Sambhajinagar",
                    "Dharashiv", "Dhule", "Gadchiroli", "Gondia", "Hingoli", "Jalgaon", "Jalna", "Kolhapur", "Latur",
                    "Mumbai City", "Mumbai Suburban", "Nagpur", "Nanded", "Nandurbar", "Nashik", "Palghar", "Parbhani", "Pune",
                    "Raigad", "Ratnagiri", "Sangli", "Satara", "Sindhudurg", "Solapur", "Thane", "Wardha", "Washim", "Yavatmal"],
    "Odisha": ["Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Boudh", "Cuttack", "Deogarh", "Dhenkanal", "Gajapati", "Ganjam",
               "Jagatsinghpur", "Jajpur", "Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara", "Kendujhar", "Khordha", "Koraput",
               "Malkangiri", "Mayurbhanj", "Nabarangpur", "Nayagarh", "Nuapada", "Puri", "Rayagada", "Sambalpur", "Subarnapur",
               "Sundargarh"],
    "Punjab": ["Amritsar", "Barnala", "Bathinda", "Faridkot", "Fatehgarh Sahib", "Fazilka", "Ferozepur", "Gurdaspur", "Hoshiarpur",
               "Jalandhar", "Kapurthala", "Ludhiana", "Malerkotla", "Mansa", "Moga", "Mohali", "Muktsar", "Nawanshahr", "Pathankot",
               "Patiala", "Rupnagar", "Sangrur", "Tarn Taran"],
    "Rajasthan": ["Ajmer", "Alwar", "Banswara", "Baran", "Barmer", "Bharatpur", "Bhilwara", "Bikaner", "Bundi", "Chittorgarh", "Churu",
                  "Dausa", "Dholpur", "Dungarpur", "Hanumangarh", "Jaipur", "Jaisalmer", "Jalore", "Jhalawar", "Jhunjhunu", "Jodhpur",
                  "Karauli", "Kota", "Nagaur", "Pali", "Pratapgarh", "Rajsamand", "Sawai Madhopur", "Sikar", "Sirohi",
                  "Sri Ganganagar", "Tonk", "Udaipur"],
    "Tamil Nadu": ["Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode", "Kallakurichi",
                   "Kanchipuram", "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam", "Namakkal",
                   "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur",
                   "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai",
                   "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar"],
    "Telangana": ["Adilabad", "Bhadradri Kothagudem", "Hanumakonda", "Hyderabad", "Jagtial", "Jangaon", "Jayashankar Bhupalpally",
                  "Jogulamba Gadwal", "Kamareddy", "Karimnagar", "Khammam", "Kumuram Bheem Asifabad", "Mahabubabad", "Mahabubnagar",
                  "Mancherial", "Medak", "Medchal-Malkajgiri", "Mulugu", "Nagarkurnool", "Nalgonda", "Narayanpet", "Nirmal",
                  "Nizamabad", "Peddapalli", "Rajanna Sircilla", "Rangareddy", "Sangareddy", "Siddipet", "Suryapet", "Vikarabad",
                  "Wanaparthy", "Warangal", "Yadadri Bhuvanagiri"],
    "Uttar Pradesh": ["Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh", "Baghpat", "Bahraich",
                      "Ballia", "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti", "Bhadohi", "Bijnor", "Budaun", "Bulandshahr",
                      "Chandauli", "Chitrakoot", "Deoria", "Etah", "Etawah", "Farrukhabad", "Fatehpur", "Firozabad",
                      "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", "Hapur", "Hardoi", "Hathras",
                      "Jalaun", "Jaunpur", "Jhansi", "Kannauj", "Kanpur Dehat", "Kanpur Nagar", "Kasganj", "Kaushambi", "Kushinagar",
                      "Lakhimpur Kheri", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri", "Mathura", "Mau", "Meerut",
                      "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit", "Pratapgarh", "Prayagraj", "Raebareli", "Rampur",
                      "Saharanpur", "Sambhal", "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shravasti", "Siddharthnagar", "Sitapur",
                      "Sonbhadra", "Sultanpur", "Unnao", "Varanasi"],
    "West Bengal": ["Alipurduar", "Bankura", "Birbhum", "Cooch Behar", "Dakshin Dinajpur", "Darjeeling", "Hooghly", "Howrah",
                    "Jalpaiguri", "Jhargram", "Kalimpong", "Kolkata", "Malda", "Murshidabad", "Nadia", "North 24 Parganas",
                    "Paschim Bardhaman", "Paschim Medinipur", "Purba Bardhaman", "Purba Medinipur", "Purulia", "South 24 Parganas",
                    "Uttar Dinajpur"],
}

# A sensible first choice when the person switches state (keeps the dashboard populated straight away).
DEFAULT_DISTRICT = {"Andhra Pradesh": "Guntur", "Bihar": "Patna", "Chhattisgarh": "Raipur", "Gujarat": "Ahmedabad",
                    "Haryana": "Karnal", "Karnataka": "Mysuru", "Madhya Pradesh": "Indore", "Maharashtra": "Pune",
                    "Odisha": "Khordha", "Punjab": "Ludhiana", "Rajasthan": "Jaipur", "Tamil Nadu": "Coimbatore",
                    "Telangana": "Hyderabad", "Uttar Pradesh": "Lucknow", "West Bengal": "Hooghly"}

# Name used for the geocoder search when it differs from the label shown to the person (tried in order).
SEARCH_ALIASES = {
    "Ahilyanagar": ["Ahmednagar"], "Chhatrapati Sambhajinagar": ["Aurangabad"], "Dharashiv": ["Osmanabad"],
    "Ballari": ["Bellary"], "Belagavi": ["Belgaum"], "Kalaburagi": ["Gulbarga"], "Mysuru": ["Mysore"], "Shivamogga": ["Shimoga"],
    "Tumakuru": ["Tumkur"], "Vijayapura": ["Bijapur"], "Bengaluru Urban": ["Bengaluru", "Bangalore"], "Bengaluru Rural": ["Doddaballapura"],
    "Gurugram": ["Gurgaon"], "Mohali": ["Sahibzada Ajit Singh Nagar"], "Nawanshahr": ["Shahid Bhagat Singh Nagar"],
    "Muktsar": ["Sri Muktsar Sahib"], "Prayagraj": ["Allahabad"], "Ayodhya": ["Faizabad"], "Raebareli": ["Rae Bareli"],
    "Kutch": ["Bhuj"], "Thoothukudi": ["Tuticorin"], "Tiruchirappalli": ["Trichy"],
    "NTR (Vijayawada)": ["Vijayawada"], "Mumbai City": ["Mumbai"], "Mumbai Suburban": ["Bandra"],
    "Kolkata": ["Calcutta"], "Cooch Behar": ["Koch Bihar"], "Medchal-Malkajgiri": ["Medchal"], "Rangareddy": ["Shamshabad"],
    "Kanpur Nagar": ["Kanpur"], "Kanpur Dehat": ["Akbarpur"], "Gautam Buddha Nagar": ["Noida"], "Ambedkar Nagar": ["Akbarpur"],
    "Janjgir-Champa": ["Janjgir"], "Kabirdham": ["Kawardha"], "Dantewada": ["Dantewara"], "Gariaband": ["Gariyaband"],
    "Anakapalli": ["Anakapalle"], "Konaseema": ["Amalapuram"], "Parvathipuram Manyam": ["Parvathipuram"],
    "Alluri Sitharama Raju": ["Paderu"], "Sri Sathya Sai": ["Puttaparthi"], "YSR Kadapa": ["Kadapa"], "Palnadu": ["Narasaraopet"],
    "Annamayya": ["Rayachoti"],
}


def states():
    return sorted(DISTRICTS)


def districts_for(state):
    return list(DISTRICTS.get(state, []))


def is_valid(state, district):
    return district in DISTRICTS.get(state, ())

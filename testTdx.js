const TDX_CONFIG = {
    clientId: "14366042-a49c7065-ce01-40be",
    clientSecret: "c66c5776-209c-4cd4-9deb-1c2ff55366b6",
    tokenUrl: "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
};

async function test() {
    const params = new URLSearchParams();
    params.append('grant_type', 'client_credentials');
    params.append('client_id', TDX_CONFIG.clientId);
    params.append('client_secret', TDX_CONFIG.clientSecret);

    const res = await fetch(TDX_CONFIG.tokenUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params
    });
    const data = await res.json();
    const token = data.access_token;
    console.log("Token:", !!token);

    if(!token) return;

    const urls = [
        "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/CarPark/City/Taipei?$top=5&$format=JSON",
        "https://tdx.transportdata.tw/api/basic/v1/Parking/OffStreet/CarPark/City/Taipei?$top=5&$format=JSON",
        "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/CCTV/City/Taipei?$top=5&$format=JSON",
        "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/CCTV/Freeway?$top=5&$format=JSON"
    ];

    for(let url of urls) {
        try {
            const r = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
            const d = await r.json();
            console.log(url);
            console.log("Length:", Array.isArray(d) ? d.length : (d.CarParks ? d.CarParks.length : 'Not Array'), d[0] || (d.CarParks && d.CarParks[0]));
        } catch(e) {
            console.error(url, e.message);
        }
    }
}
test();

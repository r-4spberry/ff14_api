document.addEventListener("DOMContentLoaded", updateDC);
document.getElementById("data_center").addEventListener("change", updateDC);
function updateDC() {
    const dcSelector = document.getElementById("data_center")
    const selectedDCname = dcSelector.value
    const selectedDC = data_centers.find(item => item.name === selectedDCname)
    const filteredWorlds = worlds.filter(item => selectedDC.worlds.includes(item.id))
    const homeWorldSelect = document.getElementById("home_world")
    homeWorldSelect.innerHTML = ""

    console.log("selectedDC", selectedDC)
    console.log("filteredWorlds", filteredWorlds)
    console.log("worlds", worlds
        
    )
    filteredWorlds.forEach(world => {
        const option = document.createElement("option")
        option.value = world.id
        option.textContent = world.name + " (" + world.id + ")"
        homeWorldSelect.appendChild(option)
    })
}